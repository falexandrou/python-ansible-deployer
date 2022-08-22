# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915
import os
import json
import pytest

import testinfra.utils.ansible_runner

PROVISIONING_OUTPUT = None
with open('./provisioning-output.json') as output:
    PROVISIONING_OUTPUT = json.load(output)

TESTINFRA_HOSTS = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']
).get_hosts('all')

MEMCACHED_PACKAGES = [
    'libmemcached-dev',
    'php-memcache',
    'php-memcached',
    'python3-memcache',
]


def test_resources_provisioned():
    assert 'cache_param_group' in PROVISIONING_OUTPUT
    assert 'cache_subnet_group' in PROVISIONING_OUTPUT

    # make sure the instance got deployed
    assert 'provision_results' in PROVISIONING_OUTPUT
    assert isinstance(PROVISIONING_OUTPUT['provision_results'], list)
    node = PROVISIONING_OUTPUT['provision_results'][0]
    assert len(PROVISIONING_OUTPUT['provision_results']) == 1

    assert node['CacheClusterId'] == 'memcached-cluster'
    assert len(node['CacheNodes']) == 1

    assert isinstance(node['SecurityGroups'], list)
    assert len(node['SecurityGroups']) == 3

    # make sure the security groups were created
    assert 'caches_sg' in PROVISIONING_OUTPUT
    group = PROVISIONING_OUTPUT['caches_sg']
    assert group['group_name'] == 'cache-incoming'

    assert 'default_sg' in PROVISIONING_OUTPUT
    group = PROVISIONING_OUTPUT['default_sg']
    assert group['group_name'] == 'default'

    assert 'stackmate_sg' in PROVISIONING_OUTPUT
    group = PROVISIONING_OUTPUT['stackmate_sg']
    assert group['group_name'] == 'stackmate-incoming'


@pytest.mark.parametrize('package', MEMCACHED_PACKAGES)
def test_package_is_installed(host, package):
    assert host.package(package).is_installed


def test_stackmate_state_generated():
    assert 'stackmate_state' in PROVISIONING_OUTPUT
    assert isinstance(PROVISIONING_OUTPUT['stackmate_state'], list)
