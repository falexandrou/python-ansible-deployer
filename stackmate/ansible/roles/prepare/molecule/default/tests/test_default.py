# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915
import json

PROVISIONING_OUTPUT = None
with open('./provisioning-output.json') as output:
    PROVISIONING_OUTPUT = json.load(output)


def test_github_key_added():
    assert 'github_deploy_key' in PROVISIONING_OUTPUT
    assert isinstance(PROVISIONING_OUTPUT['github_deploy_key'], dict)
    assert PROVISIONING_OUTPUT['github_deploy_key']
    assert PROVISIONING_OUTPUT['github_deploy_key']['key']
    assert PROVISIONING_OUTPUT['github_deploy_key']['key']['id']
    assert PROVISIONING_OUTPUT['github_deploy_key']['key']['key']


def test_aws_user_validated():
    assert 'aws_user_info' in PROVISIONING_OUTPUT
    assert isinstance(PROVISIONING_OUTPUT['aws_user_info'], dict)
    assert PROVISIONING_OUTPUT['aws_user_info']
    assert PROVISIONING_OUTPUT['aws_user_info']['account']
    assert PROVISIONING_OUTPUT['aws_user_info']['arn']


def test_stackmate_state_generated():
    assert 'stackmate_state' in PROVISIONING_OUTPUT
    assert isinstance(PROVISIONING_OUTPUT['stackmate_state'], list)
