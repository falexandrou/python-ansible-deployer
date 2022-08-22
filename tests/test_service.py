# -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915
import pytest
from stackmate.deployables import Deployable
from stackmate.deployables.service import Service, ProvisionableService, \
    StandaloneService, ManagedService
from stackmate.exceptions import ServiceNotAvailableError, ValidationError
from stackmate.configurations import StackmateConfiguration

CONFIG = StackmateConfiguration().contents
DEFAULT_SERVICE_ATTRIBUTES = []

def describe_service():
    def it_returns_all_the_available_services(project):
        available = Service.collect(project)
        assert isinstance(available, list)
        assert available
        assert all(isinstance(s, Service) for s in available)

    def it_expands_the_instances_services(project):
        # add 5 nodes to the instances role
        appserver = next(
            srv for srv in project.configuration.contents.services if srv['type'] == 'application'
        )

        assert appserver
        assert appserver['nodes'] > 1

        names = [a.name for a in Service.collect(project)]
        assert 'application-server' in names

    def it_provides_a_factory_method():
        assert hasattr(Service, 'factory')
        assert callable(Service.factory)

    def it_instantiates_a_provisionable_service_through_the_factory():
        srv = Service.factory(kind='application')
        assert isinstance(srv, Service)
        assert isinstance(srv, ProvisionableService)
        assert isinstance(srv, Deployable)

        assert hasattr(srv, 'kind')
        assert srv.kind == 'application'

        assert hasattr(srv, 'provider')
        assert srv.provider is None

        assert not hasattr(srv, 'version')

        assert hasattr(srv, 'load_balanced')
        assert srv.load_balanced

    def it_instantiates_a_standalone_service_through_the_factory():
        srv = Service.factory(kind='mysql')
        assert isinstance(srv, Service)
        assert isinstance(srv, StandaloneService)
        assert isinstance(srv, Deployable)

        assert hasattr(srv, 'version')
        assert srv.version == '5.7'

        assert hasattr(srv, 'kind')
        assert srv.kind == 'backend'

        assert hasattr(srv, 'provider')
        assert srv.provider is None

        assert hasattr(srv, 'port')
        assert srv.port == 3306

    def it_instantiates_a_managed_service_through_the_factory():
        srv = Service.factory(kind='mysql', provider='aws')
        assert isinstance(srv, Service)
        assert isinstance(srv, ManagedService)
        assert isinstance(srv, Deployable)

        assert hasattr(srv, 'version')
        assert srv.version == '5.7'

        assert hasattr(srv, 'kind')
        assert srv.kind == 'mysql'

        assert hasattr(srv, 'provider')
        assert srv.provider == 'aws'

        assert hasattr(srv, 'port')
        assert srv.port == 3306

    def it_requires_credentials_for_the_service():
        # start without credentials
        srv = Service.factory(kind='mysql', provider='aws')
        with pytest.raises(ValidationError) as validation_error:
            assert srv.validate()

        assert validation_error
        assert 'credentials' in srv.errors
        assert 'root_credentials' in srv.errors

        # Provide the credentials now
        credentials = {'username': 'user1', 'password': 'pass1'}
        srv = Service.factory(
            kind='mysql', provider='aws', credentials=credentials, root_credentials=credentials)

        with pytest.raises(ValidationError) as validation_error:
            assert srv.validate()

        assert validation_error
        assert 'credentials' not in srv.errors
        assert 'root_credentials' not in srv.errors

    def it_instantiates_a_provisionable_service_with_all_attributes():
        srv = Service.factory(
            kind='application',
            size='xlarge',
            provider='aws',
            dependencies=[{'kind': 'nginx', 'version': '1.16'}],
            credentials={'username': 'aaa', 'password': '1234'},
            root_credentials={'username': 'bbb', 'password': '4321'},
            configfiles=[{'source': '/source.txt', 'target': '/target.txt', 'application': True}],
            storage='100g')
        assert isinstance(srv, ProvisionableService)
        assert srv.kind == 'application'
        assert srv.size == 'xlarge'
        assert srv.provider == 'aws'
        assert srv.storage == '100g'
        assert hasattr(srv, 'version') is False
        assert len(srv.dependencies) == 1
        dep = srv.dependencies[0]
        assert isinstance(dep, dict)
        assert dep['kind'] == 'nginx'
        assert dep['version'] == '1.16'
        assert srv.credentials is not None
        assert srv.root_credentials is not None
        assert len(srv.configfiles) == 1

    def it_instantiates_a_standalone_service_with_all_attributes():
        srv = Service.factory(
            kind='memcached',
            provider='digitalocean',
            nodes=5,
            size='xlarge',
            credentials={'username': 'aaa', 'password': '1234'},
            root_credentials={'username': 'bbb', 'password': '4321'},
            configfiles=[{'source': '/source.txt', 'target': '/target.txt', 'application': True}],
            storage='100g')
        assert isinstance(srv, StandaloneService)
        assert srv.kind == 'backend'
        assert srv.nodes == 5
        assert srv.size == 'xlarge'
        assert srv.provider == 'digitalocean'
        assert srv.version == '1.5.17'
        assert srv.credentials is not None
        assert srv.root_credentials is not None
        assert len(srv.configfiles) == 1
        assert srv.port == 11211

    def it_instantiates_a_managed_service_with_all_attributes():
        srv = Service.factory(
            kind='memcached',
            provider='aws',
            nodes=5,
            size='xlarge',
            port=11222,
            credentials={'username': 'aaa', 'password': '1234'},
            root_credentials={'username': 'bbb', 'password': '4321'},
            storage='100g')
        assert isinstance(srv, ManagedService)
        assert srv.kind == 'memcached'
        assert srv.nodes == 5
        assert srv.size == 'xlarge'
        assert srv.provider == 'aws'
        assert srv.version == '1.5.17'
        assert srv.configfiles == []
        assert srv.managed
        assert srv.credentials is not None
        assert srv.root_credentials is not None
        assert srv.port == 11222

    def it_raises_an_exception_when_the_service_is_not_found_in_the_list_of_available_ones():
        missing_service = 'a*b*c321123'
        msg = 'The service {s} cannot be instantiated with given arguments'.format(
            s=missing_service)

        with pytest.raises(ServiceNotAvailableError) as err:
            Service.factory(kind=missing_service)
            assert err.message == msg

    def it_serializes_without_the_non_serializable_attributes():
        srv = Service.factory(kind='application')
        serialized = srv.serialize().keys()
        provision_params = srv.provision_params.keys()

        assert 'node' not in serialized
        assert 'node' not in provision_params

        assert 'dependencies' not in serialized
        assert 'dependencies' not in provision_params

        assert 'environment' not in serialized
        assert 'environment' not in provision_params

        assert 'links' not in serialized
        assert 'links' not in provision_params

# Provisionable Services
# appplication service
def describe_application_worker_and_backend_services():
    def it_has_all_entries_in_stackmate_yml():
        services = ['application', 'worker', 'backend']
        for service in services:
            assert CONFIG.get_path('services.attributes.%s' % service) is not None

    def it_instantiates_them_as_provisionable_services():
        services = ['application', 'worker', 'backend']
        dependencies = [{'kind': 'nginx', 'version': '1.17.2'}]

        for service in services:
            srv = Service.factory(kind=service, dependencies=dependencies)
            assert isinstance(srv, Service)
            assert isinstance(srv, ProvisionableService)
            assert len(srv.dependencies) == 1
            dep = srv.dependencies[0]
            assert isinstance(dep, dict)
            assert dep['kind'] == 'nginx'
            assert dep['version'] == '1.17.2'

    def it_instantiates_them_as_provisionable_services_with_provider_passed():
        services = ['application', 'worker', 'backend']
        dependencies = [{'kind': 'nginx', 'version': '1.17.2'}]
        provider = 'aws'

        for service in services:
            srv = Service.factory(kind=service, dependencies=dependencies, provider=provider)
            assert isinstance(srv, Service)
            assert isinstance(srv, ProvisionableService)
            assert srv.provider == provider


# All Services:
# MySQL
def describe_mysql_service():
    def it_has_an_entry_in_stackmate_yml():
        assert CONFIG.get_path('services.attributes.mysql') is not None
        assert 'mysql' in CONFIG.get_path('dependencies.available')
        assert 'mysql' in CONFIG.get_path('services.standalone')
        assert 'mysql' in CONFIG.get_path('services.managed.aws')
        assert 'mysql' not in CONFIG.get_path('services.managed.digitalocean')

    def it_has_all_the_attributes():
        srv = Service.factory(kind='mysql')
        assert sorted(srv.attribute_names) == sorted([
            'configfiles', 'credentials', 'dependencies', 'environment',
            'kind', 'links', 'managed', 'name', 'port', 'provider',
            'root_credentials', 'size', 'storage', 'region', 'version',
            'databases', 'engine', 'role', 'reference',
        ])

    def it_instantiates_it_as_managed_for_provider_aws():
        srv = Service.factory(kind='mysql', provider='aws')
        assert isinstance(srv, ManagedService)

    def it_instantiates_it_as_standalone_for_provider_digitalocean():
        srv = Service.factory(kind='mysql', provider='digitalocean')
        assert isinstance(srv, StandaloneService)

    def it_returns_an_empty_list_as_replacement_triggers():
        srv = Service.factory(kind='mysql', provider='aws')
        assert not srv.replacement_triggers

        srv = Service.factory(kind='mysql', provider='digitalocean')
        assert srv.replacement_triggers

# PostgreSQL
def describe_postgresql_service():
    def it_has_an_entry_in_stackmate_yml():
        assert CONFIG.get_path('services.attributes.postgresql') is not None
        assert 'postgresql' in CONFIG.get_path('dependencies.available')
        assert 'postgresql' in CONFIG.get_path('services.standalone')
        assert 'postgresql' in CONFIG.get_path('services.managed.aws')
        assert 'postgresql' in CONFIG.get_path('services.managed.digitalocean')

    def it_has_all_the_attributes():
        srv = Service.factory(kind='postgresql')
        assert sorted(srv.attribute_names) == sorted([
            'configfiles', 'credentials', 'dependencies', 'environment', 'kind',
            'links', 'managed', 'name', 'port', 'provider', 'reference',
            'root_credentials', 'size', 'storage', 'region', 'version',
            'databases', 'engine', 'role',
        ])

    def it_instantiates_it_as_managed_for_provider_aws():
        srv = Service.factory(kind='postgresql', provider='aws')
        assert isinstance(srv, ManagedService)

    def it_instantiates_it_as_managed_for_provider_digitalocean():
        srv = Service.factory(kind='postgresql', provider='digitalocean')
        assert isinstance(srv, ManagedService)

    def it_returns_an_empty_list_as_replacement_triggers():
        srv = Service.factory(kind='postgresql', provider='aws')
        assert not srv.replacement_triggers

        srv = Service.factory(kind='postgresql', provider='digitalocean')
        assert srv.replacement_triggers

# Redis
def describe_redis_service():
    def it_has_an_entry_in_stackmate_yml():
        assert CONFIG.get_path('services.attributes.redis') is not None
        assert 'redis' in CONFIG.get_path('dependencies.available')
        assert 'redis' in CONFIG.get_path('services.standalone')
        assert 'redis' in CONFIG.get_path('services.managed.aws')
        assert 'redis' not in CONFIG.get_path('services.managed.digitalocean')

    def it_has_all_the_attributes():
        srv = Service.factory(kind='redis')
        assert sorted(srv.attribute_names) == sorted([
            'configfiles', 'credentials', 'dependencies', 'environment',
            'kind', 'links', 'managed', 'name', 'port', 'provider', 'reference',
            'root_credentials', 'size', 'region', 'version', 'role', 'storage',
        ])

    def it_instantiates_it_as_managed_for_provider_aws():
        srv = Service.factory(kind='redis', provider='aws')
        assert isinstance(srv, ManagedService)

    def it_instantiates_it_as_standalone_for_provider_digitalocean():
        srv = Service.factory(kind='redis', provider='digitalocean')
        assert isinstance(srv, StandaloneService)

# Memcached
def describe_memcached_service():
    def it_has_an_entry_in_stackmate_yml():
        assert CONFIG.get_path('services.attributes.memcached') is not None
        assert 'memcached' in CONFIG.get_path('dependencies.available')
        assert 'memcached' in CONFIG.get_path('services.standalone')
        assert 'memcached' in CONFIG.get_path('services.managed.aws')
        assert 'memcached' not in CONFIG.get_path('services.managed.digitalocean')

    def it_has_all_the_attributes():
        srv = Service.factory(kind='memcached')
        assert sorted(srv.attribute_names) == sorted([
            'configfiles', 'credentials', 'dependencies', 'environment', 'reference',
            'kind', 'links', 'managed', 'name', 'nodes', 'port', 'provider',
            'root_credentials', 'size', 'region', 'version', 'role', 'storage',
        ])

    def it_instantiates_it_as_managed_for_provider_aws():
        srv = Service.factory(kind='memcached', provider='aws')
        assert isinstance(srv, ManagedService)

    def it_instantiates_it_as_standalone_for_provider_digitalocean():
        srv = Service.factory(kind='memcached', provider='digitalocean')
        assert isinstance(srv, StandaloneService)

# Email
def describe_email_service():
    def it_has_an_entry_in_stackmate_yml():
        assert CONFIG.get_path('services.attributes.mailer') is not None
        assert 'mailer' in CONFIG.get_path('dependencies.available')
        assert 'mailer' in CONFIG.get_path('services.standalone')
        assert 'mailer' in CONFIG.get_path('services.managed.aws')
        assert 'mailer' not in CONFIG.get_path('services.managed.digitalocean')

    def it_has_all_the_attributes():
        srv = Service.factory(kind='mailer')
        assert sorted(srv.attribute_names) == sorted([
            'configfiles', 'credentials', 'dependencies', 'environment', 'kind',
            'links', 'managed', 'name', 'port', 'provider', 'reference',
            'root_credentials', 'region', 'inbound', 'emails',
            'deliveries', 'faults', 'domain', 'size', 'storage', 'role',
        ])

    def it_instantiates_it_as_managed_for_provider_aws():
        srv = Service.factory(kind='mailer', provider='aws')
        assert isinstance(srv, ManagedService)

    def it_instantiates_it_as_standalone_for_provider_digitalocean():
        srv = Service.factory(kind='mailer', provider='digitalocean')
        assert isinstance(srv, StandaloneService)

# CDN
def describe_cdn_service():
    def it_has_an_entry_in_stackmate_yml():
        assert CONFIG.get_path('services.attributes.cdn') is not None
        assert 'cdn' not in CONFIG.get_path('dependencies.available')
        assert 'cdn' not in CONFIG.get_path('services.available')
        assert 'cdn' not in CONFIG.get_path('services.standalone')
        assert 'cdn' in CONFIG.get_path('services.managed.aws')
        assert 'cdn' not in CONFIG.get_path('services.managed.digitalocean')

    def it_has_all_the_attributes():
        srv = Service.factory(kind='cdn', provider='aws')
        assert isinstance(srv, ManagedService)
        assert sorted(srv.attribute_names) == sorted([
            'kind', 'managed', 'name', 'origins', 'provider', 'region',
            'environment', 'role', 'dependencies', 'reference',
        ])

    def it_raises_error_for_provider_digitalocean():
        with pytest.raises(ServiceNotAvailableError) as err:
            Service.factory(kind='cdn')
            assert err.message == 'The service cdn cannot be instantiated with given arguments'

    def it_includes_origins_in_the_list_of_replacement_triggers():
        srv = Service.factory(kind='cdn', provider='aws')
        assert sorted(srv.replacement_triggers) == sorted([
            'size', 'region', 'provider', 'storage', 'origins',
        ])

# Elastic storage
def describe_elasticstorage_service():
    def it_has_an_entry_in_stackmate_yml():
        assert CONFIG.get_path('services.attributes.elasticstorage') is not None
        assert 'elasticstorage' not in CONFIG.get_path('dependencies.available')
        assert 'elasticstorage' not in CONFIG.get_path('services.available')
        assert 'elasticstorage' not in CONFIG.get_path('services.standalone')
        assert 'elasticstorage' in CONFIG.get_path('services.managed.aws')
        assert 'elasticstorage' in CONFIG.get_path('services.managed.digitalocean')

    def it_has_all_the_attributes():
        srv = Service.factory(kind='elasticstorage', provider='aws')
        assert isinstance(srv, ManagedService)
        assert sorted(srv.attribute_names) == sorted([
            'bucket', 'kind', 'managed', 'name', 'provider', 'public',
            'role', 'region', 'website', 'environment', 'cdn', 'reference',
            'domain', 'directory_index', 'error_page', 'dependencies',
        ])

    def it_raises_error_for_provider_digitalocean():
        srv = Service.factory(kind='elasticstorage', provider='digitalocean')
        assert isinstance(srv, ManagedService)
