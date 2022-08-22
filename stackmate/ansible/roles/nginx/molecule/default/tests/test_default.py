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


def test_nginx_is_installed(host):
    assert host.package('nginx-full').is_installed


def test_nginx_service_is_enabled_and_running(host):
    nginx = host.service("nginx")
    assert nginx.is_running
    assert nginx.is_enabled


def test_custom_config_is_present(host):
    main = host.file('/etc/nginx/nginx.conf')
    assert main.exists
    assert main.is_file
    assert 'Managed by Stackmate.io' in main.content_string

    secondary = host.file('/etc/nginx/conf.d/stackmate.conf')
    assert secondary.exists
    assert secondary.is_file
    assert 'Managed by Stackmate.io' in secondary.content_string


def test_stackmate_state_generated():
    assert 'stackmate_state' in PROVISIONING_OUTPUT
    assert isinstance(PROVISIONING_OUTPUT['stackmate_state'], list)
