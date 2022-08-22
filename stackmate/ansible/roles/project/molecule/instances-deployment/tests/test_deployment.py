# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915
import re
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
    PROVISIONING_OUTPUT['release_path'],
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


def test_git_ssh_command_is_defined():
    cmd = PROVISIONING_OUTPUT['git_ssh_command']
    assert 'ssh -o IdentityFile=/home/stackmate/.ssh/stackmate'
    assert '-o UserKnownHostsFile=/dev/null' in cmd
    assert '-o StrictHostKeyChecking=no' in cmd


def test_repository_cloned(host):
    assert host.file('/var/www/djangoapp/repository/.git').is_directory
    assert host.file('/var/www/djangoapp/repository/manage.py').is_file


def test_releasedir_created(host):
    reldir = PROVISIONING_OUTPUT['release_path']
    assert re.match(r'^\/var\/www\/djangoapp\/releases\/[0-9]+\/?$', reldir)
    assert host.file(reldir).is_directory
    assert host.file('{}/manage.py'.format(reldir)).is_file


def test_symlink_created(host):
    reldir = PROVISIONING_OUTPUT['release_path']
    curdir = host.file('/var/www/djangoapp/current')
    assert curdir.exists
    assert curdir.linked_to == reldir


def test_pipeline_output():
    out = PROVISIONING_OUTPUT['pipeline_output']
    cmds = set(list([o['command'] for o in out if 'command' in o]))

    assert cmds == {
        'echo "running the pipeline"',
        'echo "db migrating"',
        'echo "db seeding"',
        'gunicorn',
        'nginx',
    }

    sysd = list([
        o['service']['name']
        for o in out if 'service' in o and o.get('changed')
    ])

    assert sysd == ['gunicorn', 'nginx']


def test_statics_synced():
    assert 'sync_output' in PROVISIONING_OUTPUT
    uploads = []
    for entry in PROVISIONING_OUTPUT['sync_output']:
        uploads += entry['filelist_s3']

    assert uploads

    s3paths = list([up['s3_path'] for up in uploads])
    assert 'admin/js/core.js' in s3paths
    assert 'appstatus/appstatus.css' in s3paths
    assert 'appstatus/appstatus.js' in s3paths


def test_release_successful():
    assert 'release_success' in PROVISIONING_OUTPUT
    assert PROVISIONING_OUTPUT['release_success']


def test_stackmate_state_generated():
    assert 'stackmate_state' in PROVISIONING_OUTPUT
    assert isinstance(PROVISIONING_OUTPUT['stackmate_state'], list)
