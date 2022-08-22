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
    'resque',
    'celery',
    'runworker',
]

SERVICE_COMMANDS = [
    ('sidekiq', dict(
        start="/usr/local/bin/bundle exec sidekiq -e production "
        + "-C config/resque.yml "
        + "-L ${SIDEKIQ_LOG_FILE}",
        stop="/usr/bin/kill -TSTP $MAINPID",
        reload="/usr/bin/kill -s HUP $MAINPID")),
    ('resque', dict(
        start="/usr/local/bin/bundle exec rake production "
        + "resque:start_workers",
        stop="/usr/local/bin/bundle exec rake production "
        + "resque:stop_workers",
        reload="/usr/bin/kill -s HUP $MAINPID")),
    ('celery', dict(
        start="celery multi start ${CELERYD_NODES} -A myapp.wsgi "
        + "--pidfile=${CELERYD_PID_FILE} --logfile=${CELERYD_LOG_FILE} "
        + "--loglevel=${CELERYD_LOG_LEVEL} ${CELERYD_OPTS}",
        stop="celery multi stopwait ${CELERYD_NODES} "
        + "--pidfile=${CELERYD_PID_FILE}",
        reload="celery multi restart ${CELERYD_NODES} -A myapp.wsgi "
        + "--pidfile=${CELERYBEAT_PID_FILE} --logfile=${CELERYD_LOG_FILE} "
        + "--loglevel=${CELERYD_LOG_LEVEL} ${CELERYD_OPTS}")),
    ('celerybeat', dict(
        start="celerybeat beat -A myapp.wsgi "
        + "--pidfile=${CELERYBEAT_PID_FILE} "
        + "--logfile=${CELERYBEAT_LOG_FILE} "
        + "--loglevel=${CELERYBEAT_LOG_LEVEL}",
        # we have specified the stop and reload commands in our playbook,
        # they should override the defaults which are "None"
        stop="explicit stop command",
        reload="/usr/bin/kill -s HUP $MAINPID")),
    ('runworker', dict(
        start="/usr/bin/python manage.py runworker",
        stop="/usr/bin/kill -TSTP $MAINPID",
        reload="/usr/bin/kill -s HUP $MAINPID")),
]


@pytest.mark.parametrize('service', SYSTEMD_SERVICES)
def test_systemd_services_created(host, service):
    file = host.file('/etc/systemd/system/{}.service'.format(service))
    assert file.exists
    assert file.contains('SyslogIdentifier={}'.format(service))


@pytest.mark.parametrize('service', SYSTEMD_SERVICES)
def test_systemd_targets_created(host, service):
    file = host.file('/etc/systemd/system/{}.target'.format(service))
    assert file.exists
    assert file.contains('Wants={}.service'.format(service))


def test_terminations(host):
    assert 'termination_results' in PROVISIONING_OUTPUT
    res = PROVISIONING_OUTPUT['termination_results']
    paths = [t['path'] for t in res if t['changed']]
    assert sorted(paths) == sorted([
        '/etc/systemd/system/sidekiq2.service',
        '/etc/systemd/system/sidekiq2.target',
        '/etc/systemd/system/sidekiq2.socket',
    ])

    assert not host.file('/etc/systemd/system/sidekiq2.service').exists
    assert not host.file('/etc/systemd/system/sidekiq2.target').exists
    assert not host.file('/etc/systemd/system/sidekiq2.socket').exists


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


def test_stackmate_state_generated():
    assert 'stackmate_state' in PROVISIONING_OUTPUT
    assert isinstance(PROVISIONING_OUTPUT['stackmate_state'], list)
    assert PROVISIONING_OUTPUT['stackmate_state']
