"""Deployables are either dependencies or services that can be deployed"""
# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod
from stackmate.base import Model, ModelAttribute
from stackmate.core.credentials import Credentials
from stackmate.configurations import STACKMATE_CONFIGURATION
from stackmate.helpers import flatten
from stackmate.resources import Resource, ResourceList
from stackmate.state import State
from stackmate.constants import CONFIG_RENAMED_ATTRIBUTES, DEPLOYABLE_KIND_TO_ROLE_MAPPING, \
                                ROLE_TO_DEPENDS_ON_MAPPING, DIFF_IGNORE_KEYS, \
                                DEPLOYABLE_KINDS_WITH_EXPANDABLE_NODES


def parse_deployable_config(cfg, **kwargs):
    """
    Parses a deployable configuration section.

    Renames attributes such as 'type' with 'kind' and 'name' to 'id'
    """
    parsed = {}

    for key, value in cfg.items():
        if key in CONFIG_RENAMED_ATTRIBUTES:
            replaced = CONFIG_RENAMED_ATTRIBUTES[key]
            parsed[replaced] = value
        else:
            parsed[key] = value

    if kwargs.get('vault') and parsed.get('kind'):
        kind = parsed.get('kind')
        vault = kwargs.get('vault')

        parsed.update({
            'credentials': Credentials.load(service=kind, vault=vault),
            'root_credentials': Credentials.load(service=kind, vault=vault, root=True)
        })

    if not parsed.get('provider') and kwargs.get('provider'):
        parsed.update({'provider': kwargs.get('provider')})

    if not parsed.get('region') and kwargs.get('region'):
        parsed.update({'region': kwargs.get('region')})

    return parsed


class Deployable(Model, ABC):
    """Represents a deployable, either a service, a dependency or utility"""
    _kind = ModelAttribute(required=True, datatype=str)
    _reference = ModelAttribute(required=False, datatype=str, serializable=True)
    _role = ModelAttribute(required=False, datatype=str, serializable=False)

    @classmethod
    @abstractmethod
    def factory(cls, **kwargs):
        """Abstract factory method"""

    @staticmethod
    @abstractmethod
    def get_deployable_subclass(kind, provider=None):
        """Abstract method that returns the subclass for the deployable (if there's one)"""

    def __init__(self, from_factory=False, **kwargs):
        if not from_factory:
            raise Exception(
                'You cannot instantiate the {c} class directly, please use the factory method',
            )

        self._credentials = {}
        self._root_credentials = {}
        self._config_files = []
        self._resource_list = None

        super().__init__(**kwargs)

    def __repr__(self):
        return '<{class_name} object id: {id}>'.format(
            class_name=self.__class__.__name__, id=id(self))

    @property
    @abstractmethod
    def host_groups(self) -> list:
        """Returns the host groups the deployable is related to"""

    @property
    def provision_params(self):
        """Returns the provision parameters to use in plays"""
        return self.serialize()

    @property
    def credentials(self):
        """Returns the credentials for the service or dependency"""
        return self._credentials

    @credentials.setter
    def credentials(self, creds):
        """Sets the credentials for the dependency or service"""
        self._credentials = creds

    @property
    def root_credentials(self):
        """Returns the root credentials for the dependency or service"""
        return self._root_credentials

    @root_credentials.setter
    def root_credentials(self, roots):
        self._root_credentials = roots

    @property
    def configfiles(self):
        """Returns the config files to be deployed for the specific dependency or service"""
        return self._config_files

    @configfiles.setter
    def configfiles(self, files):
        self._config_files = files

    @staticmethod
    def get_names_by_role(role) -> set:
        """Gets the deployable name by role"""
        return {n for n, r in DEPLOYABLE_KIND_TO_ROLE_MAPPING.items() if r == role}

    @staticmethod
    def get_role_by_kind(kind) -> str:
        """Returns the role to be used for a specific deployable kind"""
        if kind not in DEPLOYABLE_KIND_TO_ROLE_MAPPING:
            raise Exception('Deployable %s is not mapped to any role' % kind)

        return DEPLOYABLE_KIND_TO_ROLE_MAPPING[kind]

    @property
    def rolename(self):
        """Returns the role to be executed during plays"""
        return Deployable.get_role_by_kind(self.kind)

    @property
    @abstractmethod
    def deployable_id(self):
        """The deployable's ID"""

    @property
    def depends_on(self) -> list:
        """Returns the deployables that this one depends on"""
        return ROLE_TO_DEPENDS_ON_MAPPING[self.rolename]

    @property
    def nodes_expandable(self) -> bool:
        """Returns whether we should expand the nodes during provision for this deployable"""
        return self.kind in DEPLOYABLE_KINDS_WITH_EXPANDABLE_NODES and hasattr(self, 'nodes')

    def include_in_inventory(self) -> bool:
        """Returns whether we should include this deployable in the inventory"""
        # pylint: disable=R0201
        return False

    def as_resources(self) -> list:
        """Returns the deployables as a list of resources"""
        did = self.deployable_id
        params = self.provision_params
        return [
            Resource(
                id=did,
                group=group,
                provision_params=params,
                reference=params.get('reference')) for group in self.host_groups
        ]

    def as_node_resources(self) -> list:
        """Returns the deployable as a list of resources based on its nodes"""
        resources = []
        nodes = self.nodes if hasattr(self, 'nodes') and self.nodes else 1

        for i in range(nodes):
            index = i + 1
            provision_params = dict(self.provision_params).copy()
            # remove the nodes param
            provision_params.pop('nodes')

            # add the index to the name
            if provision_params.get('name'):
                provision_params.update({'name': f"{provision_params['name']}-{index}"})

            # add a list of resources for all nodes
            for group in self.host_groups:
                resources.append(
                    Resource(
                        id=self.deployable_id,
                        group=group,
                        reference=provision_params.get('reference'),
                        provision_params=provision_params
                    )
                )

        return resources

    @property
    def replacement_triggers(self):
        """Attributes that if changed, trigger a service replacement"""
        # @tech-debt
        # pylint: disable=line-too-long
        # See: https://trello.com/c/HizEhQKT/111-database-replacements-should-be-started-off-of-a-snapshot
        # We need an efficient way to replace RDS instances. For now, just accept that RDS
        # can modify all database instances
        if self.rolename == 'databases' and hasattr(self, 'provider') and self.provider == 'aws':
            return []

        cfg = STACKMATE_CONFIGURATION
        return cfg.get_path('services.replacement_triggers.default', []) + \
            cfg.get_path('services.replacement_triggers.{}'.format(self.kind), [])

    def diff_ignored_keys(self):
        """Returns the keys that should be ignored when diff-ing two deployables"""
        # pylint: disable=no-self-use
        return DIFF_IGNORE_KEYS

    def process_state(self, state: State):
        """
        Processes the project's state on the deployable
        Overload this method in order to process the state during playbook execution
        """
