# -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915
from stackmate.deployables import Deployable
from stackmate.deployables.utility import Utility, ManagedUtility, \
    ConfigFileUtility, EnvironmentUtility, JobUtility, NotificationUtility, \
    SSLCertificateUtility, SSLCertificateManagedUtility, RoutingUtility, PrerequisitesUtility, \
    PrepareUtility, ProjectUtility
from stackmate.configurations import StackmateConfiguration
from stackmate.helpers import flatten

CONFIG = StackmateConfiguration().contents
DEFAULT_UTILITY_ATTRIBUTES = ['kind', 'unique']

def describe_utility():
    def it_provides_a_factory_method():
        assert hasattr(Utility, 'factory')
        assert callable(Utility.factory)

    def it_instantiates_a_utility_through_the_factory():
        utility = Utility.factory(kind='notifications')
        assert isinstance(utility, Utility)
        assert isinstance(utility, Deployable)
        assert not isinstance(utility, ManagedUtility)

    def it_instantiates_a_provisionable_service_through_the_factory():
        utility = Utility.factory(kind='routing', provider='aws')
        assert isinstance(utility, Utility)
        assert isinstance(utility, ManagedUtility)
        assert isinstance(utility, RoutingUtility)

    def it_detects_the_subclass_by_deployable():
        # global utilities
        assert isinstance(
            Utility.get_deployable_subclass('configfiles'), ConfigFileUtility.__class__)
        assert isinstance(
            Utility.get_deployable_subclass('environment'), EnvironmentUtility.__class__)
        assert isinstance(
            Utility.get_deployable_subclass('jobschedules'), JobUtility.__class__)
        assert isinstance(
            Utility.get_deployable_subclass('notifications'), NotificationUtility.__class__)
        # managed utilities
        assert isinstance(
            Utility.get_deployable_subclass('ssl', 'aws'), SSLCertificateManagedUtility.__class__)
        assert Utility.get_deployable_subclass('ssl', 'digitalocean') is SSLCertificateUtility
        assert Utility.get_deployable_subclass('ssl') is SSLCertificateUtility

        assert isinstance(
            Utility.get_deployable_subclass('routing', 'aws'), RoutingUtility.__class__)
        assert isinstance(
            Utility.get_deployable_subclass('routing', 'digitalocean'), RoutingUtility.__class__)
        assert Utility.get_deployable_subclass('routing') is None


def describe_configfiles_utility():
    def it_has_an_entry_in_stackmate_yml():
        assert 'configfiles' in CONFIG.get_path('utilities.available')
        assert 'configfiles' not in CONFIG.get_path('services.managed.aws')
        assert 'configfiles' not in CONFIG.get_path('services.managed.digitalocean')

    def it_collects_all_configfile_utilities_from_the_configuration(provisioned_project, \
            project_services, project_dependencies):
        configs = Utility.collect(
            'configfiles', provisioned_project, project_services, project_dependencies)

        assert isinstance(configs, list)
        assert all([isinstance(u, ConfigFileUtility) for u in configs])
        # according to the fixture, there should be 3 entries
        assert len(configs) == 3
        source_names = [cfg.source for cfg in configs]
        target_names = [cfg.target for cfg in configs]
        hashes = [cfg.filehash for cfg in configs]

        assert set(source_names) == set([
            'configuration-files/nginx.conf',
            'configuration-files/database.yml',
            'configuration-files/cable.yml',
        ])

        assert set(target_names) == set([
            'config/database.yml',
            'config/cable.yml',
            'nginx.conf',
        ])

        assert all([isinstance(hsh, str) and hsh for hsh in hashes])

def describe_environment_utility():
    def it_has_an_entry_in_stackmate_yml():
        assert 'environment' in CONFIG.get_path('utilities.available')
        assert 'environment' not in CONFIG.get_path('services.managed.aws')
        assert 'environment' not in CONFIG.get_path('services.managed.digitalocean')

    def it_collects_all_environment_variables_from_the_configuration(provisioned_project, \
            project_services, project_dependencies, state):
        environments = Utility.collect(
            'environment', provisioned_project, project_services, project_dependencies)

        assert isinstance(environments, list)
        assert all([isinstance(u, EnvironmentUtility) for u in environments])
        # according to the fixture, there should be 10 entries
        assert len(environments) == 13

        for env in environments:
            env.process_state(state)

        indexed = {env.export:env.serialize() for env in environments}
        assert set(indexed.keys()) == set([
            'RAILS_ENV', 'DATABASE_MAIN_URL', 'CACHE_URL', 'CDN_URL',
            'SMTP_HOST', 'SMTP_PORT', 'SMTP_USERNAME', 'SMTP_PASSWORD', 'STORAGE_URL',
            'SERVER_0_IP', 'SERVER_1_IP', 'RAILS_ENV', 'MALLOC_ARENA_MAX', 'QUEUES',
        ])

        # according to the fixtures, these should be the environment entries
        values = {export:env.get('value') for export, env in indexed.items()}
        assert values == {
            # deployable environment vars (from the config)
            'MALLOC_ARENA_MAX': '2',
            'QUEUES': '*',
            # project environment vars
            'RAILS_ENV': 'production',
            'DATABASE_MAIN_URL': 'mysql://bbbb:bbbb@92.12.123.213:443/stackmate',
            'CACHE_URL': 'tcp://cache.something.somewhere.com:11211',
            'CDN_URL': 'cdn.some.distribution.com',
            'SMTP_HOST': 'mailer.some.distribution.com',
            'SMTP_PORT': '587',
            'SMTP_USERNAME': 'abc1234',
            'SMTP_PASSWORD': 'qwerty1',
            'STORAGE_URL': 'https://storage.something.somewhere.com/some-bucket',
            'SERVER_0_IP': 'https://92.12.123.213:443',
            'SERVER_1_IP': 'https://92.12.124.213:443',
        }


def describe_ssl_utility():
    def it_has_an_entry_in_stackmate_yml():
        assert 'ssl' in CONFIG.get_path('utilities.available')
        assert 'ssl' in CONFIG.get_path('services.managed.aws')
        assert 'ssl' not in CONFIG.get_path('services.managed.digitalocean')

    def it_has_the_correct_deployable_lookup_and_default_host_groups():
        assert SSLCertificateUtility.lookup_key() == 'ssl'
        assert SSLCertificateUtility.default_host_groups == ['application']

        assert SSLCertificateManagedUtility.lookup_key() == 'ssl'
        assert SSLCertificateManagedUtility.default_host_groups == ['localhost']

    def it_collects_the_entries_from_the_configuration(provisioned_project, \
            project_services, project_dependencies):
        certificates = Utility.collect(
            'ssl', provisioned_project, project_services, project_dependencies)

        assert isinstance(certificates, list)
        assert all([isinstance(u, SSLCertificateManagedUtility) for u in certificates])

        # according to the fixture, there should be 3 certificates:
         # 1 main, 1 for the assets and 1 for the cdn
        assert len(certificates) == 3
        maincert = certificates[0].serialize()
        assert maincert['generate']
        assert not maincert['is_cdn_certificate']
        assert set(maincert['domains']) == {
            'ezploy.eu',
            'stackmate-cli-master.stackmate.io',
        }

        cdncert = certificates[1].serialize()
        assert cdncert['generate']
        assert cdncert['is_cdn_certificate']
        assert set(cdncert['domains']) == {'ezploy.eu', 'cdn.ezploy.eu'}

        assetscert = certificates[2].serialize()
        assert assetscert['generate']
        assert assetscert['is_cdn_certificate']
        assert set(assetscert['domains']) == {'assets.ezploy.eu'}

def describe_notifications_utility():
    def it_has_an_entry_in_stackmate_yml():
        assert 'notifications' in CONFIG.get_path('utilities.available')
        assert 'notifications' not in CONFIG.get_path('services.managed.aws')
        assert 'notifications' not in CONFIG.get_path('services.managed.digitalocean')

    def it_has_the_correct_deployable_lookup_and_default_host_groups():
        assert NotificationUtility.lookup_key() == 'notifications'
        assert NotificationUtility.default_host_groups == ['localhost']

    def it_collects_the_entries_from_the_configuration(provisioned_project, \
            project_services, project_dependencies):
        notifications = Utility.collect(
            'notifications', provisioned_project, project_services, project_dependencies)

        assert isinstance(notifications, list)
        assert all([isinstance(u, NotificationUtility) for u in notifications])
        # according to the fixture, there should be 2 notifications
        # - 1 for slack under the deployments-channel
        # - 1 for email sent to johnny5@something.com
        assert len(notifications) == 2
        serialized = [n.serialize() for n in notifications]
        types = [ser['type'] for ser in serialized]
        targets = flatten([ser['targets'] for ser in serialized])
        assert set(types) == set(['email', 'slack'])
        assert set(targets) == set(['stackmateuser@mailinator.com', 'deployments-channel'])

def describe_jobschedules_utility():
    def it_has_an_entry_in_stackmate_yml():
        assert 'jobschedules' in CONFIG.get_path('utilities.available')
        assert 'jobschedules' not in CONFIG.get_path('services.managed.aws')
        assert 'jobschedules' not in CONFIG.get_path('services.managed.digitalocean')

    def it_has_the_correct_deployable_lookup_and_default_host_groups():
        assert JobUtility.lookup_key() == 'jobschedules'
        assert JobUtility.default_host_groups == ['application', 'worker']

    def it_collects_the_entries_from_the_configuration(provisioned_project, \
            project_services, project_dependencies):
        jobschedules = Utility.collect(
            'jobschedules', provisioned_project, project_services, project_dependencies)

        assert isinstance(jobschedules, list)
        assert all([isinstance(u, JobUtility) for u in jobschedules])
        # according to the fixture, there should be 2 jobschedules
        # - 1 for /bin/true every minute
        # - 1 for /bin/false every 5 minutes
        assert len(jobschedules) == 2
        host_groups = flatten([sched.host_groups for sched in jobschedules])
        serialized = [j.serialize() for j in jobschedules]
        commands = [ser['command'] for ser in serialized]
        frequencies = [ser['frequency'] for ser in serialized]
        assert set(commands) == set(['/bin/true', '/bin/false'])
        assert set(frequencies) == set(['*/1 * * * *', '*/5 * * * *'])
        assert set(host_groups) == set(['application'])

def describe_routing_utility():
    def it_has_an_entry_in_stackmate_yml():
        assert 'routing' not in CONFIG.get_path('utilities.available')
        assert 'routing' in CONFIG.get_path('services.managed.aws')
        assert 'routing' in CONFIG.get_path('services.managed.digitalocean')

    def it_has_the_correct_deployable_lookup_and_default_host_groups():
        assert RoutingUtility.lookup_key() == 'routing'
        assert RoutingUtility.default_host_groups == ['localhost']

    def it_collects_the_entries_from_the_configuration(provisioned_project, \
            project_services, project_dependencies):
        routing_entries = Utility.collect(
            'routing', provisioned_project, project_services, project_dependencies)

        assert isinstance(routing_entries, list)
        assert all([isinstance(u, RoutingUtility) for u in routing_entries])
        assert len(routing_entries) == 1

        serialized = routing_entries[0].serialize()
        assert serialized['target_port'] == 80
        assert serialized['domain'] == 'stackmate-cli-master.stackmate.io'

    def it_processes_the_state(state, project, project_services, project_dependencies):
        routings = Utility.collect(
            'routing', project, project_services, project_dependencies)

        assert isinstance(routings, list)
        assert all([isinstance(u, RoutingUtility) for u in routings])
        assert len(routings) == 1

        routing = routings[0]
        routing.process_state(state)

        serialized = routing.serialize()
        assert isinstance(serialized, dict)
        assert 'target_instances' in serialized
        assert len(serialized['target_instances']) == 2
        # instance should be something like i-abc123
        assert all(inst.startswith('i') for inst in serialized['target_instances'])

def describe_prerequisites_utility():
    def it_has_an_entry_in_stackmate_yml():
        assert 'prerequisites' not in CONFIG.get_path('utilities.available')
        assert 'prerequisites' in CONFIG.get_path('utilities.managed.aws')
        assert 'prerequisites' not in CONFIG.get_path('utilities.managed.digitalocean')

    def it_has_the_correct_deployable_lookup_and_default_host_groups():
        assert PrerequisitesUtility.lookup_key() == 'prerequisites'
        assert PrerequisitesUtility.default_host_groups == ['localhost']

    def it_collects_the_entries_from_the_configuration(provisioned_project, \
            project_services, project_dependencies):
        prereq_entries = Utility.collect(
            'prerequisites', provisioned_project, project_services, project_dependencies)

        assert isinstance(prereq_entries, list)
        assert all([isinstance(u, PrerequisitesUtility) for u in prereq_entries])
        assert all(u.deployable_id == 'utility-prerequisites' for u in prereq_entries)
        assert len(prereq_entries) == 1

        serialized = prereq_entries[0].serialize()
        assert serialized['provider'] == 'aws'
        assert serialized['scm'] == 'github'
        assert serialized['domain'] == 'stackmate-cli-master.stackmate.io'
        assert serialized['region'] == 'eu-central-1'

def describe_prepare_utility():
    def it_has_an_entry_in_stackmate_yml():
        assert 'prepare' in CONFIG.get_path('utilities.available')
        assert 'prepare' not in CONFIG.get_path('utilities.managed.aws')
        assert 'prepare' not in CONFIG.get_path('utilities.managed.digitalocean')

    def it_has_the_correct_deployable_lookup_and_default_host_groups():
        assert PrepareUtility.lookup_key() == 'prepare'
        assert PrepareUtility.default_host_groups == ['localhost']

    def it_collects_the_entries_from_the_configuration(provisioned_project, \
            project_services, project_dependencies):
        prep_entries = Utility.collect(
            'prepare', provisioned_project, project_services, project_dependencies)

        assert isinstance(prep_entries, list)
        assert all([isinstance(u, PrepareUtility) for u in prep_entries])
        assert all(pr.deployable_id == 'utility-prepare' for pr in prep_entries)
        assert len(prep_entries) == 1

        serialized = prep_entries[0].serialize()
        assert serialized['repository'] == 'git@github.com:stackmate-io/stackmate-cli.git'
        assert serialized['scm'] == 'github'

def describe_project_utility():
    def it_has_an_entry_in_stackmate_yml():
        assert 'project' in CONFIG.get_path('utilities.available')
        assert 'project' not in CONFIG.get_path('utilities.managed.aws')
        assert 'project' not in CONFIG.get_path('utilities.managed.digitalocean')

    def it_has_the_correct_deployable_lookup_and_default_host_groups():
        assert ProjectUtility.lookup_key() == 'project'
        assert ProjectUtility.default_host_groups == ['application', 'workers']

    def it_collects_the_entries_from_the_configuration(provisioned_project, \
            project_services, project_dependencies):
        prep_entries = Utility.collect(
            'project', provisioned_project, project_services, project_dependencies)

        assert isinstance(prep_entries, list)
        assert all([isinstance(u, ProjectUtility) for u in prep_entries])
        assert len(prep_entries) == 1

        serialized = prep_entries[0].serialize()
        assert prep_entries[0].deployable_id == 'utility-project'
        assert serialized['kind'] == 'project'
        assert serialized['provider'] == 'aws'
        assert serialized['repository'] == 'git@github.com:stackmate-io/stackmate-cli.git'
        assert serialized['github_deploy_key_name'] == 'Stackmate Deploy Key'
        assert isinstance(serialized['appconfigs'], list)
        assert sorted(serialized['appconfigs']) == sorted([
            'config/database.yml', 'config/cable.yml',
        ])
        daemons = {
            'celery', 'daphne', 'gunicorn', 'nginx', 'pm2',
            'puma', 'resque', 'runworker', 'sidekiq',
        }
        assert serialized['daemons'] == {'application': daemons, 'workers': daemons}
        assert serialized['pipeline'] == dict(provisioned_project.configuration.contents.pipeline)
