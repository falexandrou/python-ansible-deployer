# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915
import json

PROVISIONING_OUTPUT = None
with open('./provisioning-output.json') as output:
    PROVISIONING_OUTPUT = json.load(output)


def test_instances_provisioned():
    assert 'provision_results' in PROVISIONING_OUTPUT
    assert isinstance(PROVISIONING_OUTPUT['provision_results'], list)
    assert len(PROVISIONING_OUTPUT['provision_results']) == 2

    # make sure the instance got properly provisioned
    instance = PROVISIONING_OUTPUT['provision_results'][0]
    assert isinstance(instance, dict)
    assert instance['key_name'] == 'molecule-test'

    sgs = list([sg['group_name'] for sg in instance['security_groups']])
    expected_sgs = [
        'stackmate-ssh',
        'application-incoming',
    ]

    assert sorted(sgs) == sorted(expected_sgs)


def test_instances_terminated():
    assert 'termination_results' in PROVISIONING_OUTPUT
    assert isinstance(PROVISIONING_OUTPUT['termination_results'], list)
    assert len(PROVISIONING_OUTPUT['termination_results']) == 2

    # make sure the instance got properly provisioned
    instance = PROVISIONING_OUTPUT['termination_results'][0]
    assert isinstance(instance, dict)
    assert instance['key_name'] == 'molecule-test'
    assert instance['state']['name'] in ['terminated', 'shutting-down']


def test_prerequisites_provisioned():
    assert 'keypair' in PROVISIONING_OUTPUT
    assert PROVISIONING_OUTPUT['keypair']['key']['name'] == 'molecule-test'

    assert 'stackmate_sg' in PROVISIONING_OUTPUT
    assert PROVISIONING_OUTPUT['stackmate_sg']['group_name'] == 'stackmate-ssh'

    assert 'application_sg' in PROVISIONING_OUTPUT
    group_name = PROVISIONING_OUTPUT['application_sg']['group_name']
    assert group_name == 'application-incoming'


def test_prerequisites_terminated():
    assert 'terminated_stackmate_sg' in PROVISIONING_OUTPUT
    assert PROVISIONING_OUTPUT['terminated_stackmate_sg']['changed']

    assert 'terminated_application_sg' in PROVISIONING_OUTPUT
    assert PROVISIONING_OUTPUT['terminated_application_sg']['changed']

    assert 'terminated_keypair' in PROVISIONING_OUTPUT
    assert PROVISIONING_OUTPUT['terminated_keypair']['changed']


def test_stackmate_state_generated():
    assert 'stackmate_state' in PROVISIONING_OUTPUT
    assert isinstance(PROVISIONING_OUTPUT['stackmate_state'], list)
