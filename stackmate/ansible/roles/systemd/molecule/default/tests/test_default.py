# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915
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

SYSTEMD_SERVICES = [
    'sidekiq',
    'celery',
]

SERVICE_COMMANDS = [
    ('sidekiq', dict(
        start="/bin/bash -lc '/usr/bin/bundle exec sidekiq -e production'",
        stop="/usr/bin/kill -TSTP $MAINPID",
        reload=None)),
    ('celery', dict(
        start="/bin/sh -c 'celery multi start'",
        stop="/bin/sh -c 'celery multi stopwait'",
        reload="/bin/sh -c 'celery multi restart'")),
]


@pytest.mark.parametrize('service', SYSTEMD_SERVICES)
def test_systemd_services_created(host, service):
    filename = '/etc/systemd/system/{}.service'.format(service)
    file = host.file(filename)
    assert file.exists
    assert file.contains('SyslogIdentifier={}'.format(service))


@pytest.mark.parametrize('service', SYSTEMD_SERVICES)
def test_systemd_targets_created(host, service):
    filename = '/etc/systemd/system/{}.target'.format(service)
    file = host.file(filename)
    assert file.exists
    assert file.contains('Wants={}.service'.format(service))


@pytest.mark.parametrize('commandset', SERVICE_COMMANDS)
def test_commands(host, commandset):
    service, commands = commandset

    filename = '/etc/systemd/system/{}.service'.format(service)
    file = host.file(filename)

    cmdmap = dict(start='ExecStart', stop='ExecStop', reload='ExecReload')

    for key, cmd in commands.items():
        if cmd is not None:
            lookup = '%s=%s' % (cmdmap[key], cmd)
            assert file.contains(lookup)
        else:
            assert not file.contains('{}='.format(cmdmap[key]))


def test_terminations(host):
    assert 'termination_results' in PROVISIONING_OUTPUT
    res = PROVISIONING_OUTPUT['termination_results']
    paths = [t['path'] for t in res if t['changed']]
    changed = {t['path']: t['changed'] for t in res}

    assert paths == [
        '/etc/systemd/system/celerybeat.service',
        '/etc/systemd/system/celerybeat.target',
    ]

    assert changed == {
        '/etc/systemd/system/celerybeat.service': True,
        '/etc/systemd/system/celerybeat.target': True,
        '/etc/systemd/system/celerybeat.socket': False,
    }

    assert not host.file('/etc/systemd/system/celerybeat.service').exists
    assert not host.file('/etc/systemd/system/celerybeat.target').exists
