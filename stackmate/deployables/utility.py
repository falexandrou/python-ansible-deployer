"""
A utility can either be a deployable much like a dependency
or a managed service, depending on the provider.

Utilities are provider-agnostic otherwise they're managed services
"""
# -*- coding: utf-8 -*-
import os
import json
from abc import abstractmethod
from jinja2 import Template
from stackmate.base import ModelAttribute
from stackmate.constants import LOCALHOST
from stackmate.deployables import Deployable, parse_deployable_config
from stackmate.exceptions import UtilityNotAvailableError
from stackmate.configurations import STACKMATE_CONFIGURATION
from stackmate.helpers import file_contents_hash, string_hash, jinja_safe
from stackmate.helpers import flatten, get_scm_service
from stackmate.state import State


class Utility(Deployable):
    """
    Represents a deployable utility
    """
    _unique = ModelAttribute(required=False, default=False, datatype=bool)

    # The default host_groups where the utility should run
    default_host_groups = [LOCALHOST]

    @staticmethod
    @abstractmethod
    def lookup_key():
        """The key to use for lookups in the project configuration and services"""

    @classmethod
    @abstractmethod
    def gather_entries(cls, project, services, dependencies):
        """Gathers the entries for the utility"""

    @classmethod
    def factory(cls, **kwargs):
        """Factory method that instantiates a utility"""
        config = parse_deployable_config(kwargs)

        kind = config.get('kind')
        if not kind:
            raise ValueError('You have to provide the name of the utility to instantiate')

        attributes = STACKMATE_CONFIGURATION.get_path(
            'utilities.attributes.{kind}'.format(kind=kind), {})

        # get the utility's dedicated class
        utility_class = Utility.get_deployable_subclass(kind, provider=config.get('provider'))

        if not utility_class:
            raise UtilityNotAvailableError('There is no utility class for utility %s' % kind)

        # process the dynamic model attributes
        setup = {attr: ModelAttribute(name=attr, **opts) for attr, opts in attributes.items()}
        # form the utility init arguments
        init_args = dict(model_setup=setup, from_factory=True, **config)

        return utility_class(**init_args)

    @staticmethod
    def get_deployable_subclass(kind, provider=None):
        """Utilities have dedicated sub-classes, this method detects which class to instantiate"""
        try:
            managed = set(STACKMATE_CONFIGURATION.get_path('utilities.managed.%s' % provider, []))
            if provider and managed and kind in managed:
                return next(
                    c for c in ManagedUtility.__subclasses__() if c.lookup_key() == kind
                )

            available = STACKMATE_CONFIGURATION.get_path('utilities.available')
            if available and kind in available:
                return next(
                    c for c in Utility.__subclasses__() if c.lookup_key() == kind
                )
        except StopIteration:
            return None

        return None

    @staticmethod
    def available(provider) -> set:
        """Returns the utility available for a specific provider"""
        return set(
            STACKMATE_CONFIGURATION.get_path('utilities.available', []) +
            STACKMATE_CONFIGURATION.get_path('utilities.managed.%s' % provider, [])
        )

    @staticmethod
    def collect(kind, project, services, dependencies=None):
        """Collects the utilities that are available in the project"""
        # Utilities have their own subclasses
        utility_class = Utility.get_deployable_subclass(kind, project.provider)

        if not utility_class:
            raise UtilityNotAvailableError('There is no utility class for utility %s' % kind)

        util_entries = utility_class.gather_entries(project, services, dependencies)
        utilities = []

        for attr_list, host_groups, parent in util_entries:
            for attributes in attr_list:
                nodes = 1

                # take into account deployables that spawn accross multiple nodes
                has_nodes = isinstance(parent, Deployable) and hasattr(parent, 'nodes')
                if has_nodes and utility_class.is_indexable(attributes):
                    nodes = parent.nodes

                for index in range(nodes):
                    attributes.update({'index': index})

                    util = utility_class.factory(
                        kind=kind,
                        provider=project.provider,
                        project=project,
                        host_groups=host_groups,
                        parent=parent,
                        attributes=attributes)

                    utilities.append(util)

        return utilities

    @classmethod
    def is_indexable(cls, attributes):
        """Returns whether we should use the `index` for the utilitie's entries"""

    def __init__(self, **kwargs):
        self._host_groups = kwargs.get('host_groups', self.default_host_groups)
        self.parent = kwargs.get('parent')
        self.project = kwargs.get('project')
        attributes = kwargs.get('attributes', {})
        self.__serialized = None
        super().__init__(**attributes, **kwargs)

    def get_id_suffix(self):
        """Returns the suffix to use in the deployable's ID"""

    @property
    def deployable_id(self):
        """The deployable's ID. It should be unique and idempotent"""
        return 'utility-%s-%s' % (self.kind, self.get_id_suffix())

    @property
    def host_groups(self):
        """Returns the host groups the utility is tarteting"""
        return self._host_groups or Utility.default_host_groups

    @classmethod
    def filter_host_groups(cls, services, groups):
        """Filters a list of host groups by what's available in the project"""
        return set(groups) & set(flatten([srv.host_groups for srv in services]))


class ManagedUtility(Utility):
    """Utilities that are provided as managed services"""
    default_host_groups = [LOCALHOST]

    _provider = ModelAttribute(required=False, datatype=str, \
        choices=STACKMATE_CONFIGURATION.get_path('providers'))

    @staticmethod
    def lookup_key():
        return None

    @classmethod
    @abstractmethod
    def gather_entries(cls, project, services, dependencies):
        """Remains abstract"""

    def include_in_inventory(self) -> bool:
        """Returns whether we should include this deployable in the inventory"""
        # pylint: disable=R0201
        return True


class SSLCertificateUtility(Utility):
    """Represents a SSL Certificate utility"""
    default_host_groups = ['application']

    @staticmethod
    def lookup_key():
        return 'ssl'

    @classmethod
    def cdn_certificate_region(cls, default_region, provider):
        """Returns the region to use for the certificate"""
        return 'us-central-1' if provider == 'aws' else default_region

    @classmethod
    def gather_entries(cls, project, services, dependencies):
        # pylint: disable=too-many-locals
        entries = []

        # parse the main domain and its aliases first
        main_ssl = project.configuration.contents.get_path('ssl', {})
        main_domains = set(main_ssl.get('domains', []))

        if project.domain:
            main_domains.add(project.domain)

        if main_domains:
            main_attrs = {
                'region': project.region,
                'is_cdn_certificate': False,
                'domains': list(main_domains),
            }

            entries.append(
                ([main_attrs], cls.default_host_groups, None)
            )

        # parse the CDN services next
        cdn_services = [srv for srv in services if srv.kind == 'cdn']
        for cdn in cdn_services:
            origins = cdn.origins or []
            domains = [[orig.get('domain', [])] + orig.get('aliases', []) for orig in origins]
            entries.append(
                (
                    [{
                        'is_cdn_certificate': True,
                        'domains': list(flatten(domains)),
                        'region': cls.cdn_certificate_region(project.region, project.provider),
                    }],
                    cls.default_host_groups,
                    None,
                ),
            )

        # parse elasticstorage services that include a domain
        es_services = [srv for srv in services if srv.kind == 'elasticstorage']
        for essrv in es_services:
            has_cdn_attr = hasattr(essrv, 'cdn') and essrv.cdn
            has_domain_attr = hasattr(essrv, 'domain') and essrv.domain

            if not has_cdn_attr and not has_domain_attr:
                continue

            entries.append(
                (
                    [{
                        'is_cdn_certificate': True,
                        'domains': list([essrv.domain]),
                        'region': cls.cdn_certificate_region(project.region, project.provider),
                    }],
                    cls.default_host_groups,
                    None,
                )
            )

        return entries

    def get_id_suffix(self):
        """Returns the suffix to use in the deployable's ID"""
        hashable = json.dumps({
            'is_cdn_certificate': self.is_cdn_certificate,
            'domains': list(self.domains),
        })

        return string_hash(hashable)

    @property
    def deployable_id(self):
        """The deployable's ID. It should be unique and idempotent"""
        return 'utility-ssl-{suffix}'.format(suffix=self.get_id_suffix())


class SSLCertificateManagedUtility(ManagedUtility):
    """Represents a SSL Certificate utility"""
    @staticmethod
    def lookup_key():
        return SSLCertificateUtility.lookup_key()

    @classmethod
    def gather_entries(cls, project, services, dependencies):
        return SSLCertificateUtility.gather_entries(project, services, dependencies)

    def get_id_suffix(self):
        """Returns the suffix to use in the deployable's ID"""
        hashable = json.dumps({
            'is_cdn_certificate': self.is_cdn_certificate,
            'domains': list(self.domains),
        })

        return string_hash(hashable)

    @property
    def deployable_id(self):
        """The deployable's ID. It should be unique and idempotent"""
        return 'utility-ssl-{suffix}'.format(suffix=self.get_id_suffix())


class ConfigFileUtility(Utility):
    """Hndles the config file utility"""
    default_host_groups = ['application', 'worker']

    @staticmethod
    def lookup_key():
        return 'configfiles'

    @property
    def filehash(self):
        """The file's hash"""
        return self.get_file_hash(self.source)

    @filehash.setter
    def filehash(self, filehash):
        """Dummy setter"""

    def get_file_hash(self, file):
        """Returns the file's md5 hash"""
        return file_contents_hash(os.path.join(self.project.rootpath, file))

    @classmethod
    def gather_entries(cls, project, services, dependencies):
        lookup_key = cls.lookup_key()

        entries = []

        if project.configfiles:
            entries.append((project.configfiles, cls.default_host_groups, None))

        # Config files can be applied to both services & dependencies
        deployables = services + dependencies

        for deployable in deployables:
            if not hasattr(deployable, lookup_key):
                continue

            configfiles = getattr(deployable, lookup_key)
            if not configfiles:
                continue

            entries.append((configfiles, deployable.host_groups, deployable))

        return entries

    def get_id_suffix(self):
        """Returns the suffix to use in the deployable's ID"""
        return string_hash(self.source)


class EnvironmentUtility(Utility):
    """Utility that handles environment configurations"""
    default_host_groups = ['application', 'worker']
    _value = ModelAttribute(required=False, datatype=str, default='')
    _raw = ModelAttribute(required=False, datatype=str, default='', serializable=False)
    _index = ModelAttribute(required=False, datatype=int, default=0, serializable=False)

    @staticmethod
    def lookup_key():
        return 'environment'

    @classmethod
    def extract_envs(cls, subject, host_groups):
        """Extracts environment entries from object configurations"""
        lookup_key = cls.lookup_key()
        default_envs = {}

        if isinstance(subject, Deployable):
            default_envs = dict(STACKMATE_CONFIGURATION.get_path(
                'default_environment.{kind}'.format(kind=subject.kind), {}))

        parent = subject if isinstance(subject, Deployable) else None
        exports = [
            {'export': exp, 'value': str(val), 'raw': str(val)} for exp, val in default_envs.items()
        ]

        if not hasattr(subject, lookup_key):
            return (exports, host_groups, parent)

        envs = getattr(subject, lookup_key)

        if not envs:
            return (exports, host_groups, parent)

        if not isinstance(envs, dict):
            raise ValueError('Entries for the environment utility should be a dictionary')

        exports += [
            {'export': exp, 'value': str(val), 'raw': str(val)} for exp, val in envs.items()
        ]

        return (exports, host_groups, parent)

    @classmethod
    def is_indexable(cls, attributes):
        """Returns whether we should use the `index` for the utilitie's entries"""
        return 'export' in attributes and '{{index}}' in attributes['export']

    @classmethod
    def gather_entries(cls, project, services, dependencies):
        entries = []
        host_groups = cls.filter_host_groups(services, cls.default_host_groups)
        subjects = [project] + services + dependencies

        for subject in subjects:
            exports = cls.extract_envs(subject, host_groups)

            if not exports:
                continue

            entries.append(exports)

        return entries

    def get_id_suffix(self):
        """Returns the suffix to use in the deployable's ID"""
        return string_hash(self.export)

    def process_state(self, state: State):
        """Processes the state"""
        # Now that the state is in place, refresh the values according to it
        if not self.parent or not isinstance(self.parent, Deployable):
            return

        parent_resources = state.get_deployable_resources(self.parent)
        if not parent_resources:
            return

        if len(parent_resources) > 1:
            raise Exception(
                'State holds more than 1 resources deployable "{id}" of type "{d}"'.format(
                    id=self.parent.deployable_id, d=self.parent.kind))

        [resource] = parent_resources.all
        output = dict(resource.output)
        substitutions = dict(**resource.output, index=self.index)

        # The deployable spawns across many nodes and there's the placeholder '{{index}}'
        # in the *export* template, this means we have to replace the host with the address
        # of the corresponding node
        if output.get('nodes', []) and self.is_indexable(self.attributes):
            cnt = len(output['nodes'])

            if self.index not in range(cnt):
                msg = 'Environment utility gathered an entry with index {idx} ' + \
                    'but the "{name}" {dep} deployable spawns across {cnt} nodes'

                raise Exception(msg.format(
                    name=self.parent.name, dep=self.parent.kind, idx=self.index, cnt=cnt))

            # replace the current host with the corresponding node
            node = output['nodes'][self.index]
            substitutions.update(node)
            substitutions.update({'host': node.get('host') or node.get('ip')})

        # Finally render the value and key making sure that it's safe to render in jinja
        self.set_attribute(
            'value', jinja_safe(Template(str(self.raw or '')).render(**substitutions)))
        self.set_attribute(
            'export', jinja_safe(Template(str(self.export or '')).render(**substitutions)))


class JobUtility(Utility):
    """Utility that provisions scheduled jobs in a project"""
    default_host_groups = ['application', 'worker']

    @staticmethod
    def lookup_key():
        return 'jobschedules'

    @classmethod
    def gather_entries(cls, project, services, dependencies) -> list:
        """
        Gathers the job entries. If a worker service is present,
        it uses that. Otherwise it uses the application service.
        """
        has_worker = any([srv.kind == 'worker' for srv in services])

        # job schedules should be at root level
        jobschedules = project.configuration.contents.get_path('jobschedules') or []
        if not jobschedules:
            return []

        return [
            (jobschedules, ['worker'] if has_worker else ['application'], None),
        ]

    def get_id_suffix(self):
        """Returns the suffix to use in the deployable's ID"""
        return string_hash(self.command)


class NotificationUtility(Utility):
    """Utility that handles the notifications after deployment has succeeded / failed"""
    # The default host_groups where the utility should run
    default_host_groups = [LOCALHOST]

    @staticmethod
    def lookup_key():
        return 'notifications'

    @classmethod
    def gather_entries(cls, project, services, dependencies):
        notifications = project.configuration.contents.get_path('notifications')

        if not notifications:
            return []

        entries = []
        for notif in notifications:
            entries.append(([notif], cls.default_host_groups, None,))

        return entries

    def get_id_suffix(self):
        """Returns the suffix to use in the deployable's ID"""
        return string_hash(self.type)

    @property
    def deployable_id(self):
        """The deployable's ID. It should be unique and idempotent"""
        return 'utility-project'

class RoutingUtility(ManagedUtility):
    """Represents a load balancer"""
    DEFAULT_PORT = 80

    @staticmethod
    def lookup_key():
        return 'routing'

    @classmethod
    def gather_entries(cls, project, services, dependencies):
        entries = []

        routables = [srv for srv in services if srv.load_balanced]
        root_domain = project.configuration.contents.get('domain')

        for srv in routables:
            domain = srv.domain if hasattr(srv, 'domain') else root_domain
            loadbalancers = []

            for group in srv.host_groups:
                loadbalancers.append({
                    'target_group': group,
                    'target_port': srv.port if hasattr(srv, 'port') else cls.DEFAULT_PORT,
                    'domain': domain,
                })

            entries.append(
                (loadbalancers, srv.host_groups, srv,)
            )

        return entries

    def get_id_suffix(self):
        """Returns the suffix to use in the deployable's ID"""
        hashable = json.dumps({
            'target_port': self.target_port,
            'domain': self.domain,
        })

        return string_hash(hashable)

    def process_state(self, state: State):
        """Processes the state"""
        # Now that the state is in place, refresh the values according to it
        if not self.parent or not isinstance(self.parent, Deployable):
            return

        parent_resources = state.get_deployable_resources(self.parent)
        if not parent_resources:
            return

        target_instances = []
        for resource in parent_resources.all:
            output = dict(resource.output)
            if not self.parent.nodes_expandable and output.get('resource_id'):
                target_instances.append(output['resource_id'])
            elif output.get('nodes'):
                target_instances += list([n['resource_id'] for n in output['nodes']])

        self.set_attribute('target_instances', target_instances)


class PrerequisitesUtility(ManagedUtility):
    """Handles the prerequisites for the project in the cloud provider"""
    @staticmethod
    def lookup_key():
        return 'prerequisites'

    @classmethod
    def gather_entries(cls, project, services, dependencies):
        variables = [{
            'scm': get_scm_service(project.repository),
            'domain': project.configuration.contents.get('domain'),
            'region': project.region,
        }]

        return [
            (variables, cls.default_host_groups, None),
        ]

    @property
    def deployable_id(self):
        """The deployable's ID. It should be unique and idempotent"""
        return 'utility-prerequisites'


class EssentialsUtility(Utility):
    """Handles the prepare role"""
    @staticmethod
    def lookup_key():
        return 'essentials'

    @classmethod
    def gather_entries(cls, project, services, dependencies):
        # This utility only applies to provisionable instances
        if not any(srv.rolename == 'instances' for srv in services):
            return []

        variables = [{
            'scm': get_scm_service(project.repository),
            'repository': project.repository,
        }]

        return [
            (variables, cls.default_host_groups, None)
        ]

    @property
    def deployable_id(self):
        """The deployable's ID. It should be unique and idempotent"""
        return 'utility-essentials'


class PrepareUtility(Utility):
    """Handles the prepare role"""
    @staticmethod
    def lookup_key():
        return 'prepare'

    @classmethod
    def gather_entries(cls, project, services, dependencies):
        variables = [{
            'scm': get_scm_service(project.repository),
            'repository': project.repository,
        }]

        return [
            (variables, cls.default_host_groups, None)
        ]

    @property
    def deployable_id(self):
        """The deployable's ID. It should be unique and idempotent"""
        return 'utility-prepare'


class ProjectUtility(Utility):
    """Handles the project role"""
    DAEMON_ROLES = {'nginx', 'workers', 'appservers'}
    default_host_groups = ['application', 'workers']

    @staticmethod
    def lookup_key():
        return 'project'

    @staticmethod
    def get_daemons():
        """Gets the daemons"""

    @classmethod
    def gather_entries(cls, project, services, dependencies):
        cfg = project.configuration.contents
        pipeline = dict(cfg.pipeline) if hasattr(cfg, 'pipeline') else {}
        projectconfigs = cfg.get_path('configfiles', {})

        daemons = {
            name for role in cls.DAEMON_ROLES for name in Deployable.get_names_by_role(role)
        }

        appconfigs = [
            cf['target'] for cf in projectconfigs if cf.get('application', False)
        ]

        entries = [{
            'framework': project.framework,
            'scm': get_scm_service(project.repository),
            'repository': project.repository,
            'github_deploy_key_name': 'Stackmate Deploy Key',
            'appconfigs': appconfigs,
            'daemons': {g: daemons for g in cls.default_host_groups},
            'pipeline': pipeline,
            'statics': project.statics or [],
            'deployment_path': project.documentroot,
        }]

        return [
            (entries, cls.default_host_groups, None),
        ]

    @property
    def deployable_id(self):
        """The deployable's ID. It should be unique and idempotent"""
        return 'utility-project'

    def get_id_suffix(self):
        """Returns the suffix to use in the deployable's ID"""
        hashable = json.dumps({
            'scm': self.scm,
            'framework': self.framework,
            'repository': self.repository,
            'branch': self.branch,
            'provider': self.provider,
            'documentroot': self.documentroot,
        })

        return string_hash(hashable)

    def diff_ignored_keys(self):
        """Returns the keys that should be ignored when diff-ing two deployables"""
        # pylint: disable=no-self-use
        return super().diff_ignored_keys() + ['release_path', 'release_success', 'removed_releases']
