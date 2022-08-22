# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915
# import re
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

DIRECTORIES = [
    '/var/www/djangoapp',
    '/var/www/djangoapp/releases',
    '/var/www/djangoapp/repository',
    '/var/www/djangoapp/shared',
]

KEPT_RELEASES = [
    '/var/www/djangoapp/releases/20200122011700',
    '/var/www/djangoapp/releases/20200115113000',
    '/var/www/djangoapp/releases/20200113103000',
    '/var/www/djangoapp/releases/20200105103000',
    '/var/www/djangoapp/releases/20200102103000',
]

OBSOLETE_RELEASES = [
    '/var/www/djangoapp/releases/20191219103000',
    '/var/www/djangoapp/releases/20191214103000',
    '/var/www/djangoapp/releases/20191212103000',
    '/var/www/djangoapp/releases/20191210103000',
]


@pytest.mark.parametrize('directory', DIRECTORIES)
def test_directory_structure_exists(host, directory):
    target = host.file(directory)
    assert target.exists
    assert target.is_directory
    assert target.user == 'stackmate'
    assert target.group == 'stackmate'


def test_private_key_exists(host):
    keyfile = host.file('/home/stackmate/.ssh/stackmate')
    assert keyfile.exists
    assert oct(keyfile.mode) == '0o600'


def test_public_key_exists(host):
    keyfile = host.file('/home/stackmate/.ssh/stackmate.pub')
    assert keyfile.exists
    assert oct(keyfile.mode) == '0o644'


def test_gets_the_correct_release_to_roll_back_to():
    assert 'target_release' in PROVISIONING_OUTPUT
    target = PROVISIONING_OUTPUT['target_release']
    assert target == '/var/www/djangoapp/releases/20200115113000'


def test_current_is_linked_to_the_correct_dir(host):
    reldir = '/var/www/djangoapp/releases/20200115113000/'
    curdir = host.file('/var/www/djangoapp/current')
    assert curdir.exists
    assert '{}/'.format(curdir.linked_to) == reldir


@pytest.mark.parametrize('dirname', OBSOLETE_RELEASES)
def test_obsolete_dirs_are_missing(host, dirname):
    assert not host.file(dirname).exists


@pytest.mark.parametrize('dirname', KEPT_RELEASES)
def test_last_releases_are_kept(host, dirname):
    assert host.file(dirname).exists


def test_release_successful():
    assert 'release_success' in PROVISIONING_OUTPUT
    assert PROVISIONING_OUTPUT['release_success']


def test_stackmate_state_generated():
    assert 'stackmate_state' in PROVISIONING_OUTPUT
    assert isinstance(PROVISIONING_OUTPUT['stackmate_state'], list)
