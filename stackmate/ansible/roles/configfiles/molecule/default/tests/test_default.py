# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915
import os
import json

import testinfra.utils.ansible_runner

TESTINFRA_HOSTS = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']
).get_hosts('all')

PROVISIONING_OUTPUT = None
with open('./provisioning-output.json') as output:
    PROVISIONING_OUTPUT = json.load(output)


def test_new_files_created(host):
    file = host.file('/opt/some/other/directory/thenewfile.txt')
    assert file.exists
    assert file.contains('newfile')


def test_modifiable_files_written(host):
    file = host.file('/opt/someotherdirectory/modifiable.txt')
    assert file.exists
    assert file.contains('modifiable')
    assert not file.contains('some content to be modified')


def test_removable_files_deleted(host):
    file = host.file('/opt/removable.txt')
    assert not file.exists


def test_stackmate_state_generated():
    assert 'stackmate_state' in PROVISIONING_OUTPUT
    assert isinstance(PROVISIONING_OUTPUT['stackmate_state'], list)
