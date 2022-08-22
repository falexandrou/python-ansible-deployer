"""The service types that are available in the system"""
# -*- coding: utf-8 -*-
from stackmate.base import ModelAttribute
from stackmate.deployables import Deployable, parse_deployable_config
from stackmate.exceptions import ServiceNotAvailableError
from stackmate.configurations import STACKMATE_CONFIGURATION
from stackmate.constants import LOAD_BALANCED_SERVICES


class Service(Deployable):
    """Service launched (or to be launched) in a project's scope"""
    _name = ModelAttribute(required=True, datatype=str)
    _provider = ModelAttribute(required=False, datatype=str, \
        choices=STACKMATE_CONFIGURATION.get_path('providers'))
    _managed = ModelAttribute(required=True, datatype=bool, default=False)
    _dependencies = ModelAttribute(required=False, datatype=list, default=[], serializable=False)

    @staticmethod
    def get_deployable_subclass(kind, provider=None):
        """Determine the class to be instantiated"""
        managed = set(STACKMATE_CONFIGURATION.get_path('services.managed.{}'.format(provider), []))
        if managed and kind in managed:
            return ManagedService

        standalone = set(STACKMATE_CONFIGURATION.get_path('services.standalone', [])) - managed
        if kind in standalone:
            return StandaloneService

        provisionable = set(STACKMATE_CONFIGURATION.get_path('services.available', []))
        if kind in provisionable:
            return ProvisionableService

        return None

    @classmethod
    def factory(cls, **kwargs):
        """Instantiate the correct deployable"""
        config = parse_deployable_config(kwargs)

        kind = config.get('kind')
        provider = config.get('provider')

        if not kind:
            raise ValueError('You have to provide the service to instantiate')

        attributes = STACKMATE_CONFIGURATION.get_path('services.attributes.{kind}'.format(
            kind=kind)) or {}

        setup = {
            attr: ModelAttribute(name=attr, **opts) for attr, opts in attributes.items() if opts
        }

        service_args = dict(from_factory=True, model_setup=setup, **config)

        service_class = Service.get_deployable_subclass(kind, provider)

        if not service_class:
            raise ServiceNotAvailableError('There is no such service {}'.format(kind))

        return service_class(**service_args)

    @staticmethod
    def collect(project):
        """Collect all the services of a kind available"""
        # get all the services that are available in the project
        opts = {
            'vault': project.vault,
            'provider': project.provider,
            'region': project.region,
        }

        services = []
        for cfg in project.services:
            parsed = parse_deployable_config(cfg, **opts)
            services.append(Service.factory(**parsed))

        return services

    @property
    def deployable_id(self):
        """The deployable's ID"""
        return 'service-%s-%s' % (self.kind, self.name)

    @property
    def host_groups(self):
        """Return the host group which the service is located under (service's name by default"""
        return [self.kind]

    @property
    def load_balanced(self) -> bool:
        """Returns whether the current service is load balanced"""
        return self.kind in LOAD_BALANCED_SERVICES

    def include_in_inventory(self) -> bool:
        """Returns whether we should include this deployable in the inventory"""
        # pylint: disable=R0201
        return True


class ProvisionableService(Service):
    """Represents a service that can be provisioned with dependencies"""
    _port = ModelAttribute(required=False, datatype=int)
    _size = ModelAttribute(required=True, datatype=str)
    _storage = ModelAttribute(required=True, datatype=int)
    _credentials = ModelAttribute(required=True, default={}, datatype=dict)
    _root_credentials = ModelAttribute(required=True, default={}, datatype=dict)
    _configfiles = ModelAttribute(required=False, default=[], datatype=list)
    _environment = ModelAttribute(required=False, datatype=list, default={}, serializable=False)
    _links = ModelAttribute(required=False, datatype=list, default=[], serializable=False)


class StandaloneService(ProvisionableService):
    """Service that should be a standalone instance (or load balanced group of instances)"""
    def __init__(self, kind=None, **kwargs):
        # Launch a 'backend' service and use the service kind as the dependency kind
        kind = 'backend' # force the type to be backend
        super().__init__(**dict(kind=kind, **kwargs))


class ManagedService(Service):
    """Represents a service that is managed by a cloud provider"""
    _managed = ModelAttribute(required=True, datatype=bool, default=True)

    @property
    def configfiles(self): # pylint: disable=no-self-use
        """Managed services don't have configs"""
        return []

    @configfiles.setter
    def configfiles(self, files):
        """Override the configfiles attributes setter"""
