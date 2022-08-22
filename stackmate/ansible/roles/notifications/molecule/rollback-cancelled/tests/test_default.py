# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915
import json

PROVISIONING_OUTPUT = None
with open('./provisioning-output.json') as output:
    PROVISIONING_OUTPUT = json.load(output)


def test_slack_notifications_sent():
    assert 'notifications_output' in PROVISIONING_OUTPUT
    assert 'slack' in PROVISIONING_OUTPUT['notifications_output']
    out = PROVISIONING_OUTPUT['notifications_output']['slack']
    assert all((entry['msg'] == 'OK' for entry in out))
