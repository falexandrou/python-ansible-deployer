# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915
import os
import json
import pytest
import testinfra.utils.ansible_runner

TESTINFRA_HOSTS = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']
).get_hosts('all')

PYTHON_PACKAGES = [
    'python3-setuptools',
    'python3-dev',
    'python3-mysqldb',
    'python3-postgresql',
    'python-sqlite',
]

PROVISIONING_OUTPUT = None
with open('./provisioning-output.json') as output:
    PROVISIONING_OUTPUT = json.load(output)


def test_python_is_installed(host):
    assert host.package('python3.8').is_installed
    assert host.package('python3-apt').is_installed
    assert host.package('python3-pip').is_installed


def test_python_symlinks_are_present(host):
    assert host.file('/usr/bin/python').linked_to == '/usr/bin/python3.8'
    assert host.file('/usr/bin/pip').linked_to == '/usr/bin/pip3'


@pytest.mark.parametrize('package', PYTHON_PACKAGES)
def test_packages_installed(host, package):
    assert host.package(package).is_installed


def test_stackmate_state_generated():
    assert 'stackmate_state' in PROVISIONING_OUTPUT
    assert isinstance(PROVISIONING_OUTPUT['stackmate_state'], list)
    assert PROVISIONING_OUTPUT['stackmate_state']
