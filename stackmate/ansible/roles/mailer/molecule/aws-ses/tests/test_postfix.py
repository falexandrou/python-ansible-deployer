# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915
import os
import json
import testinfra.utils.ansible_runner

PROVISIONING_OUTPUT = None
with open('./provisioning-output.json') as output:
    PROVISIONING_OUTPUT = json.load(output)

TESTINFRA_HOSTS = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']
).get_hosts('all')


def test_postfix_is_installed(host):
    assert host.package('postfix').is_installed
    # executables are in place
    assert host.file('/usr/sbin/sendmail').exists
    assert host.file('/usr/sbin/postfix').exists
    # directories are in place
    assert host.file('/etc/postfix').is_directory
    # postfix config is in place
    cfg = host.file('/etc/postfix/main.cf')
    assert cfg.exists
    assert cfg.size

    assert 'smtp_credentials' in PROVISIONING_OUTPUT
    assert 'result' in PROVISIONING_OUTPUT['smtp_credentials']
    credentials = PROVISIONING_OUTPUT['smtp_credentials']['result']
    assert credentials

    line = 'relayhost = [{server}]:{port}'.format(
        server=credentials['server'],
        port=credentials['port'])

    assert line in cfg.content_string

    with host.sudo():
        pwdfile = host.file('/etc/postfix/sasl_passwd')
        assert pwdfile.exists
        assert pwdfile.size

        line = '[{server}]:{port} {uname}:{pwd}'.format(
            server=credentials['server'],
            port=credentials['port'],
            uname=credentials['username'],
            pwd=credentials['password'])

        assert line in pwdfile.content_string
