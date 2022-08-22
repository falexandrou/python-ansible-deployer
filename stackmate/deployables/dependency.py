"""
Dependencies that can be deployed in the systems
"""
# -*- coding: utf-8 -*-
from stackmate.base import ModelAttribute
from stackmate.deployables import Deployable, parse_deployable_config
from stackmate.exceptions import DependencyNotAvailableError
from stackmate.configurations import STACKMATE_CONFIGURATION

class Dependency(Deployable):
    """
    Represents a dependency in the system.

    A dependency can be a software dependency or a managed service
    """
    _version = ModelAttribute(required=False, datatype=str)
    _unique = ModelAttribute(required=False, default=False, datatype=bool)
    _port = ModelAttribute(required=False, datatype=int)
    _configfiles = ModelAttribute(required=False, default=[], datatype=list)
    _credentials = ModelAttribute(required=False, default={}, datatype=dict)
    _root_credentials = ModelAttribute(required=False, default={}, datatype=dict)

    @staticmethod
    def get_deployable_subclass(kind, provider=None):
        """Determine the class to be instantiated"""
        return Dependency

    @classmethod
    def factory(cls, **kwargs):
        """Instantiate the correct deployable"""
        kind = kwargs.get('kind')
        host_groups = []

        if kwargs.get('service'):
            host_groups = kwargs['service'].host_groups

        if not kind:
            raise ValueError('You have to provide the dependency to instantiate')

        available = set(STACKMATE_CONFIGURATION.get_path('dependencies.available', []))
        if available and kind not in available:
            raise DependencyNotAvailableError(
                'The dependency named {n} is not available in Stackmate'.format(n=kind))

        attributes = STACKMATE_CONFIGURATION.get_path('dependencies.attributes.{kind}'.format(
            kind=kind)) or {}

        setup = {
            attr: ModelAttribute(name=attr, **opts) for attr, opts in attributes.items() if opts
        }

        setup['version'] = ModelAttribute(
            required=True,
            datatype=str,
            choices=STACKMATE_CONFIGURATION.get_path('versions.{d}.available'.format(d=kind)),
            default=STACKMATE_CONFIGURATION.get_path('versions.{d}.default'.format(d=kind))
        )

        return Dependency(model_setup=setup, from_factory=True, host_groups=host_groups, **kwargs)

    @staticmethod
    def collect(project, services):
        """Collect all the services of a kind available"""
        # pylint: disable=W0613
        # get all the services that are available in the project
        dependencies = []

        for srv in services:
            if not hasattr(srv, 'dependencies'):
                continue

            for dependency in srv.dependencies:
                cfg = parse_deployable_config(dependency)

                if not cfg['kind'] in dependencies:
                    dependencies.append(Dependency.factory(service=srv, **cfg))

        return dependencies

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._host_groups = kwargs.get('host_groups')
        self._service = kwargs.get('service')

    @property
    def deployable_id(self):
        """The deployable's ID"""
        if self._service:
            return 'dependency-%s-%s' % (self._service.name, self.kind)
        return 'dependency-%s' % self.kind

    @property
    def host_groups(self):
        """The host group to provision the dependency in"""
        return self._host_groups
