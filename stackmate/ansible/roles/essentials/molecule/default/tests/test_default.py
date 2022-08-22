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

PYTHON_PACKAGES = [
    'python3',
    'python3-pip',
    'python3-dev',
    'python3-setuptools',
]


def test_gpg_is_installed(host):
    assert host.package('gpg').is_installed


def test_git_is_installed(host):
    assert host.package('git').is_installed


def test_sudo_is_installed(host):
    assert host.package('sudo').is_installed


def test_curl_is_installed(host):
    assert host.package('curl').is_installed
    assert host.package('libcurl4-openssl-dev').is_installed


def test_ntp_is_installed(host):
    assert host.package('ntp').is_installed
    assert host.service('ntp').is_enabled
    assert host.service('ntp').is_running
    assert host.file('/etc/ntp.conf').exists


def test_docker_is_installed(host):
    assert host.package('docker.io').is_installed


def test_openssl_is_installed(host):
    assert host.package('openssl').is_installed
    assert host.package('libssl-dev').is_installed


def test_htop_is_installed(host):
    assert host.package('htop').is_installed


def test_vim_is_installed(host):
    assert host.package('vim').is_installed


def test_rsync_is_installed(host):
    assert host.package('rsync').is_installed


def test_build_essential_is_installed(host):
    assert host.package('build-essential').is_installed


@pytest.mark.parametrize('package', PYTHON_PACKAGES)
def test_python_packages_are_installed(host, package):
    assert host.package(package).is_installed


def test_wget_is_installed(host):
    assert host.package('wget').is_installed


def test_the_user_was_created(host):
    user = host.user('stackmate')
    assert user.home == '/home/stackmate'
    print(user.groups)
    assert user.groups.sort() == [
        'wheel', 'users', 'stackmate', 'docker'].sort()


def test_the_ssh_server_is_installed_and_properly_configured(host):
    assert host.package('openssh-server').is_installed
    assert host.service('ssh').is_enabled
    assert host.service('ssh').is_running

    cfg = host.file('/etc/ssh/sshd_config')
    assert cfg.exists

    contents = str(cfg.content)
    # make sure the lines are commented out
    assert 'UsePAM yes' in contents
    assert '#UsePAM' not in contents

    assert 'PermitRootLogin no' in contents
    assert '#PermitRootLogin' not in contents

    assert 'PasswordAuthentication no' in contents
    assert '#PasswordAuthentication' not in contents


def test_stackmate_state_generated():
    assert 'stackmate_state' in PROVISIONING_OUTPUT
    assert isinstance(PROVISIONING_OUTPUT['stackmate_state'], list)
