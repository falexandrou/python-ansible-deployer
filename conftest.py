"""Stackmate Tests setup"""
# -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612
import os
import pytest
from doubles import allow
from stackmate.constants import ENV_MITOGEN_PATH, ENV_PRIVATE_KEY, ENV_PUBLIC_KEY
from stackmate.configurations import ProjectConfiguration, ProjectVault
from stackmate.deployables.service import Service
from stackmate.deployables.dependency import Dependency
from stackmate.project import Project
from stackmate.resources import ResourceList
from stackmate.state import State
from stackmate.playbooks import PlaybookIterator

# export the required environment variables
MOCK_USER_PATH = os.path.join(os.path.abspath('.'), 'tests', 'data', 'ssh-keys')
os.environ[ENV_PUBLIC_KEY] = os.path.join(MOCK_USER_PATH, 'stackmate.key.pub')
os.environ[ENV_PRIVATE_KEY] = os.path.join(MOCK_USER_PATH, 'stackmate.key')
os.environ[ENV_MITOGEN_PATH] = os.path.join(
    os.path.expanduser('~'), '.ansible', 'mitogen-0.2.9', 'ansible_mitogen', 'plugins', 'strategy')

PROJECT_PATH = os.path.join(os.getcwd(), 'tests', 'data', 'mock-project')
STAGE = 'production'
PROVIDER_AWS = 'aws'
REGION_EU = 'eu-central-1'
INTEGRATION_TESTS_SAMPLE_APPS = os.path.abspath('../stackmate-sample-apps')

def get_service_config(service):
    """Returns a service's configuration"""
    cfg = ProjectConfiguration(PROJECT_PATH, STAGE)
    srv = next(s for s in cfg.contents.services if s.get('type') == service)
    # use the credentials in the state without the vault
    srv.update({
        'credentials': {'username': 'bbbb', 'password': 'bbbb'},
        'root_credentials': {'username': 'aaaa', 'password': 'aaaa'}})

    return srv

@pytest.fixture()
def project_path():
    return PROJECT_PATH

@pytest.fixture()
def vault():
    return ProjectVault(PROJECT_PATH)

@pytest.fixture
def project_config():
    return ProjectConfiguration(PROJECT_PATH, STAGE)

@pytest.fixture
def stage():
    return STAGE

@pytest.fixture
def project():
    return Project.load(rootpath=PROJECT_PATH, stage=STAGE)

@pytest.fixture
def state():
    project_state = State(rootpath=PROJECT_PATH, stage=STAGE)
    allow(project_state).save.and_return(True)
    return project_state

@pytest.fixture
def application_service():
    return Service.factory(provider=PROVIDER_AWS, region=REGION_EU, \
        **get_service_config('application'))

@pytest.fixture
def application_service_multinode():
    config = get_service_config('application')
    config.update({'nodes': 3})
    return Service.factory(provider=PROVIDER_AWS, region=REGION_EU, **config)

@pytest.fixture
def mysql_service():
    return Service.factory(provider=PROVIDER_AWS, region=REGION_EU, \
        **get_service_config('mysql'))

@pytest.fixture
def cdn_service():
    return Service.factory(provider=PROVIDER_AWS, region=REGION_EU, \
        **get_service_config('cdn'))

@pytest.fixture
def mailer_service():
    return Service.factory(provider=PROVIDER_AWS, region=REGION_EU, \
        **get_service_config('mailer'))

@pytest.fixture
def mysql_modified():
    cfg = get_service_config('mysql')
    cfg.update({'size': 'db.t2.xlarge'})

    return Service.factory(provider=PROVIDER_AWS, region=REGION_EU, **cfg)

@pytest.fixture
def nginx_dependency():
    service = Service.factory(**get_service_config('application'))
    return Dependency.factory(kind='nginx', service=service)

@pytest.fixture
def puma_dependency():
    service = Service.factory(**get_service_config('application'))
    return Dependency.factory(kind='puma', service=service)

@pytest.fixture
def python_dependency():
    service = Service.factory(**get_service_config('application'))
    return Dependency.factory(kind='python', service=service)

@pytest.fixture
def provisioned_project():
    """Returns a project which has its infrastructure already provisioned supposedly"""
    # TODO: Fix
    proj = Project.load(rootpath=PROJECT_PATH, stage=STAGE)
    proj_state = State(rootpath=PROJECT_PATH, stage=STAGE)
    service_names = proj_state.contents.keys()

    # allow original service resources to be returned (as in the state.yml)
    service_resources = {srv: proj_state.get_resources(srv) for srv in service_names}

    # Now, apply the supposed modifications in the project's state
    # (ie. mysql should have only 1 resource left)
    service_resources['databases'] = ResourceList(
        resources=proj_state.get_resources('databases').all[:1])

    allow(proj_state).get_resources.and_return_result_of(lambda sid: service_resources[sid])

    return proj

@pytest.fixture
def project_services():
    proj = Project.load(rootpath=PROJECT_PATH, stage=STAGE)
    return [srv for srv in proj.deployables if isinstance(srv, Service)]

@pytest.fixture
def project_dependencies():
    proj = Project.load(rootpath=PROJECT_PATH, stage=STAGE)
    return [dep for dep in proj.deployables if isinstance(dep, Dependency)]

@pytest.fixture
def unprovisioned_project():
    """Returns a project which has its infrastructure already provisioned supposedly"""
    return Project.load(rootpath=PROJECT_PATH, stage='staging')

@pytest.fixture
def playbook_iterator():
    proj = Project.load(rootpath=PROJECT_PATH, stage=STAGE)
    proj_state = State(rootpath=PROJECT_PATH, stage=STAGE)
    return PlaybookIterator('deployment', proj, proj_state)

@pytest.fixture
def sinatra_app_path():
    return os.path.join(INTEGRATION_TESTS_SAMPLE_APPS, 'sinatraapp', '.stackmate')

@pytest.fixture
def static_site_path():
    return os.path.join(INTEGRATION_TESTS_SAMPLE_APPS, 'staticsite', '.stackmate')

@pytest.fixture
def django_app_path():
    return os.path.join(INTEGRATION_TESTS_SAMPLE_APPS, 'django3app', '.stackmate')

@pytest.fixture
def rails_app_path():
    return os.path.join(INTEGRATION_TESTS_SAMPLE_APPS, 'railsapp', '.stackmate')

@pytest.fixture
def nodejs_app_path():
    return os.path.join(INTEGRATION_TESTS_SAMPLE_APPS, 'expressjsapp', '.stackmate')

@pytest.fixture
def database_facts():
    # pylint: disable=line-too-long
    return [
        {
            "resources": [
                {
                    "created_at": "2020-02-28 18:13:56.598972",
                    "group": "databases",
                    "id": "service-mysql-mysql-database",
                    "output": {
                        "host": "mysql-database.chwtiyrsoyvd.eu-central-1.rds.amazonaws.com",
                        "ip": None,
                        "nodes": [],
                        "port": 3306,
                        "resource_id": "mysql-database",
                        "username": 'myuser',
                        'password': 'mypassword',
                        'root_username': 'root_db_user',
                        'root_password': 'root_db_password',
                    },
                    "provision_params": {
                        "configfiles": [],
                        "credentials": {
                            "password": "mypassword",
                            "username": "myuser"
                        },
                        "databases": [
                            "stackmate"
                        ],
                        "engine": "mysql",
                        "kind": "mysql",
                        "name": "mysql-database",
                        "nodes": 1,
                        "port": 3306,
                        "provider": "aws",
                        "region": "eu-central-1",
                        "root_credentials": {
                            "password": "root_db_password",
                            "username": "root_db_user"
                        },
                        "size": "db.t2.micro",
                        "storage": 100,
                        "version": 5.7
                    },
                    "result": {
                        "allocated_storage": 100,
                        "associated_roles": [],
                        "auto_minor_version_upgrade": True,
                        "availability_zone": "eu-central-1a",
                        "backup_retention_period": 90,
                        "ca_certificate_identifier": "rds-ca-2019",
                        "changed": True,
                        "copy_tags_to_snapshot": True,
                        "db_instance_arn": "arn:aws:rds:eu-central-1:xxxxxx:db:mysql-database",
                        "db_instance_class": "db.t2.micro",
                        "db_instance_identifier": "mysql-database",
                        "db_instance_port": 0,
                        "db_instance_status": "available",
                        "db_parameter_groups": [
                            {
                                "db_parameter_group_name": "stackmate-mysql-57",
                                "parameter_apply_status": "in-sync"
                            }
                        ],
                        "db_security_groups": [],
                        "db_subnet_group": {
                            "db_subnet_group_description": "Stackmate RDS subnet group",
                            "db_subnet_group_name": "test-rds-subnet-group",
                            "subnet_group_status": "Complete",
                            "subnets": [
                                {
                                    "subnet_availability_zone": {
                                        "name": "eu-central-1b"
                                    },
                                    "subnet_identifier": "subnet-0e6064c08d80b3014",
                                    "subnet_status": "Active"
                                },
                                {
                                    "subnet_availability_zone": {
                                        "name": "eu-central-1a"
                                    },
                                    "subnet_identifier": "subnet-02eacc03ad59e4568",
                                    "subnet_status": "Active"
                                }
                            ],
                            "vpc_id": "vpc-09ebb623125812dd5"
                        },
                        "dbi_resource_id": "db-KDJ6VQPCILOUGX5TODWSOA3Q6Y",
                        "deletion_protection": False,
                        "domain_memberships": [],
                        "endpoint": {
                            "address": "mysql-database.xxxxxxx.eu-central-1.rds.amazonaws.com",
                            "hosted_zone_id": "Z1RLNUO7XXXXXX",
                            "port": 3306
                        },
                        "engine": "mysql",
                        "engine_version": "5.7.26",
                        "failed": False,
                        "iam_database_authentication_enabled": False,
                        "instance_create_time": "2020-02-28T16:08:08.160000+00:00",
                        "latest_restorable_time": "2020-02-28T16:09:18.313000+00:00",
                        "license_model": "general-public-license",
                        "master_username": "root_db_user",
                        "monitoring_interval": 0,
                        "multi_az": False,
                        "option_group_memberships": [
                            {
                                "option_group_name": "default:mysql-5-7",
                                "status": "in-sync"
                            }
                        ],
                        "pending_modified_values": {},
                        "performance_insights_enabled": False,
                        "preferred_backup_window": "03:29-03:59",
                        "preferred_maintenance_window": "thu:23:58-fri:00:28",
                        "publicly_accessible": True,
                        "read_replica_db_instance_identifiers": [],
                        "storage_encrypted": False,
                        "storage_type": "gp3",
                        "tags": {
                            "Environment": "molecule-test",
                            "Group": "databases"
                        },
                        "vpc_security_groups": [
                            {
                                "status": "active",
                                "vpc_security_group_id": "sg-022e8fe23c87b6bde"
                            },
                            {
                                "status": "active",
                                "vpc_security_group_id": "sg-07b578ac4a92791a5"
                            },
                            {
                                "status": "active",
                                "vpc_security_group_id": "sg-0a82e0d7d52b128fa"
                            }
                        ]
                    },
                    "tainted": False
                }
            ],
            "role": "databases"
        }
    ]


@pytest.fixture
def worker_facts():
    return  [
        {
            "resources": [
                {
                    "created_at": "2020-02-07 17:26:57.994912",
                    "group": "workers",
                    "id": "dep-workers-sidekiq",
                    "output": None,
                    "provision_params": {
                        "kind": "sidekiq",
                        "name": "sidekiq"
                    },
                    "result": None,
                    "tainted": False,
                },
                {
                    "created_at": "2020-02-07 17:26:57.995571",
                    "group": "workers",
                    "id": "dep-workers-resque",
                    "output": None,
                    "provision_params": {
                        "kind": "resque",
                        "name": "resque"
                    },
                    "result": None,
                    "tainted": False,
                },
                {
                    "created_at": "2020-02-07 17:26:57.995841",
                    "group": "workers",
                    "id": "dep-workers-celery",
                    "output": None,
                    "provision_params": {
                        "kind": "celery",
                        "name": "celery"
                    },
                    "result": None,
                    "tainted": False,
                },
                {
                    "created_at": "2020-02-07 17:26:57.996105",
                    "group": "application",
                    "id": "dep-workers-celerybeat",
                    "output": None,
                    "provision_params": {
                        "config": {
                            "commands": {
                                "reload": "dummy reload celerybeat",
                                "stop": "dummy stop celerybeat"
                            }
                        },
                        "kind": "celerybeat",
                        "name": "celerybeat"
                    },
                    "result": None,
                    "tainted": False,
                },
                {
                    "created_at": "2020-02-07 17:26:57.996368",
                    "group": "application",
                    "id": "dep-workers-runworker",
                    "output": None,
                    "provision_params": {
                        "kind": "runworker",
                        "name": "runworker"
                    },
                    "result": None,
                    "tainted": False,
                }
            ],
            "role": "workers"
        }
    ]
