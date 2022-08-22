# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915
import os
import json
import pytest
import testinfra.utils.ansible_runner

TESTINFRA_HOSTS = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']
).get_hosts('all')

PROVISIONING_OUTPUT = None
with open('./provisioning-output.json') as output:
    PROVISIONING_OUTPUT = json.load(output)

MYSQL_PACKAGES = [
    'libmysqlclient-dev',
    'mysql-client',
    'mysql-common',
]


@pytest.mark.parametrize('package', MYSQL_PACKAGES)
def test_package_is_installed(host, package):
    assert host.package(package).is_installed


def test_resources_deployed():
    # make sure the instance got deployed
    assert 'deployed_output' in PROVISIONING_OUTPUT
    assert isinstance(PROVISIONING_OUTPUT['deployed_output'], dict)
    result = PROVISIONING_OUTPUT['deployed_output']
    assert result['db_instance_identifier'] == 'mysql-database'

    assert 'rds_instances' in PROVISIONING_OUTPUT
    assert isinstance(PROVISIONING_OUTPUT['rds_instances'], list)
    assert len(PROVISIONING_OUTPUT['rds_instances']) == 1

    # make sure the security groups were created
    assert 'databases_sg' in PROVISIONING_OUTPUT
    group = PROVISIONING_OUTPUT['databases_sg']
    assert group['group_name'] == 'database-incoming'

    assert 'default_sg' in PROVISIONING_OUTPUT
    group = PROVISIONING_OUTPUT['default_sg']
    assert group['group_name'] == 'default'

    assert 'stackmate_sg' in PROVISIONING_OUTPUT
    group = PROVISIONING_OUTPUT['stackmate_sg']
    assert group['group_name'] == 'stackmate-incoming'

    assert isinstance(result['vpc_security_groups'], list)
    assert len(result['vpc_security_groups']) == 3


def test_mysql_users_and_databases_created():
    assert 'mysql_user_created' in PROVISIONING_OUTPUT
    assert isinstance(PROVISIONING_OUTPUT['mysql_user_created'], dict)
    assert PROVISIONING_OUTPUT['mysql_user_created']['changed']
    assert PROVISIONING_OUTPUT['mysql_user_created']['user'] == 'myuser'

    assert 'mysql_database_created' in PROVISIONING_OUTPUT
    assert isinstance(PROVISIONING_OUTPUT['mysql_database_created'], dict)
    res = PROVISIONING_OUTPUT['mysql_database_created']['results']
    assert isinstance(res, list)
    assert res[0]['changed']
    assert res[0]['database'] == 'stackmate'


def test_stackmate_state_generated():
    assert 'stackmate_state' in PROVISIONING_OUTPUT
    assert isinstance(PROVISIONING_OUTPUT['stackmate_state'], list)
