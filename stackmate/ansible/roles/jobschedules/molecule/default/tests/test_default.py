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


def test_crontabs_activated(host):
    with host.sudo():
        cron = host.file('/var/spool/cron/crontabs/stackmate')
        assert cron.exists
        assert '*/1 * * * * /bin/true' in cron.content_string
        assert '*/5 * * * * /bin/false' in cron.content_string
        assert '*/30 * * * * /bin/something' not in cron.content_string


def test_stackmate_state_generated():
    assert 'stackmate_state' in PROVISIONING_OUTPUT
    assert isinstance(PROVISIONING_OUTPUT['stackmate_state'], list)
