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

PROVISIONS = {
    'DATABASE_MAIN_URL': 'mysql://bbbb:bbbb@92.12.123.213:443/stackmate',
    'RAILS_ENV': 'production',
    'SMTP_PASSWORD': 'qwerty1',
    'CDN_URL': 'cdn.some.distribution.com',
    'SMTP_USERNAME': 'abc1234',
    'INTERNAL_URL': 'https://abc.alb.something.somewhere.com:80',
    'STORAGE_URL': 'https://storage.something.somewhere.com/some-bucket',
    'SMTP_HOST': 'mailer.some.distribution.com',
}

MODIFICATIONS = {
    'SMTP_PORT': 587,
}

TERMINATIONS = {
    'SOME_TEST_URL': 'https://example.com',
}


def test_new_files_created(host):
    file = host.file('/etc/stackmate.env')
    assert file.exists


def test_new_exports_were_added(host):
    file = host.file('/etc/stackmate.env')
    for name, value in PROVISIONS.items():
        entry = '{name}="{value}"'.format(name=name, value=value)
        assert file.contains(entry)
        assert not file.contains('export {}'.format(entry))


def test_exports_updated(host):
    file = host.file('/etc/stackmate.env')
    # make sure the value added in the pre_tasks section
    # of the playbook does not exist
    assert not file.contains('SMTP_PORT="12345"')
    for name, value in MODIFICATIONS.items():
        entry = '{name}="{value}"'.format(name=name, value=value)
        assert file.contains(entry)
        assert not file.contains('export {}'.format(entry))


def test_missing_group_file_not_created(host):
    file = host.file('/etc/stackmate.env')

    for name, value in TERMINATIONS.items():
        entry = '{name}="{value}"'.format(name=name, value=value)
        assert not file.contains(entry)


def test_stackmate_state_generated():
    assert 'stackmate_state' in PROVISIONING_OUTPUT
    assert isinstance(PROVISIONING_OUTPUT['stackmate_state'], list)
