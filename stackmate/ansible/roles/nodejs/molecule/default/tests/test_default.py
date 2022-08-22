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

NODE_PACKAGES = [
    'node-mysql',
]


def test_node_is_installed(host):
    assert host.package('nodejs').is_installed
    # executables are in place
    assert host.file('/usr/bin/npm').exists
    assert host.file('/usr/bin/node').exists
    # directories are in place
    assert host.file('/usr/local/lib/npm').is_directory
    assert host.file('/usr/local/lib/npm/lib/node_modules').is_directory
    # global packages are in place
    assert host.file('/usr/local/lib/npm/bin/yarn').exists


@pytest.mark.parametrize('package', NODE_PACKAGES)
def test_packages_installed(host, package):
    assert host.package(package).is_installed


def test_stackmate_state_generated():
    assert 'stackmate_state' in PROVISIONING_OUTPUT
    assert isinstance(PROVISIONING_OUTPUT['stackmate_state'], list)
