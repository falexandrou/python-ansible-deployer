# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915
import os
import json
import pytest
import testinfra.utils.ansible_runner

TESTINFRA_HOSTS = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']
).get_hosts('all')


RUBY_VERSION = '2.7.2'
PROVISIONING_OUTPUT = None
with open('./provisioning-output.json') as output:
    PROVISIONING_OUTPUT = json.load(output)

RUBY_PACKAGES = [
    'ruby-mysql2',
    'ruby-pg',
    'ruby-sqlite3',
    'ruby-dataobjects-sqlite3',
]


def test_ruby_is_installed(host):
    assert host.file('/home/stackmate/.rvm/scripts/rvm').exists
    assert host.file('/home/stackmate/.rvm/rubies/').is_directory
    assert host.file(
        f'/home/stackmate/.rvm/rubies/ruby-{RUBY_VERSION}/').is_directory
    assert host.file(
        f'/home/stackmate/.rvm/rubies/ruby-{RUBY_VERSION}/bin/bundle').exists
    assert host.file(
        f'/home/stackmate/.rvm/rubies/ruby-{RUBY_VERSION}/bin/ruby').exists


@pytest.mark.parametrize('package', RUBY_PACKAGES)
def test_packages_installed(host, package):
    assert host.package(package).is_installed


def test_stackmate_state_generated():
    assert 'stackmate_state' in PROVISIONING_OUTPUT
    assert isinstance(PROVISIONING_OUTPUT['stackmate_state'], list)
    assert PROVISIONING_OUTPUT['stackmate_state']
