# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915
import json

PROVISIONING_OUTPUT = None
with open('./provisioning-output.json') as output:
    PROVISIONING_OUTPUT = json.load(output)


def test_filesystem_created():
    assert 'provisioned_volumes' in PROVISIONING_OUTPUT
    assert isinstance(PROVISIONING_OUTPUT['provisioned_volumes'], list)
    assert isinstance(PROVISIONING_OUTPUT['provisioned_volumes'][0], dict)
    vol = PROVISIONING_OUTPUT['provisioned_volumes'][0]
    assert vol['name'] == 'application-server-volume'

    assert 'provisioned_mounts' in PROVISIONING_OUTPUT
    assert isinstance(PROVISIONING_OUTPUT['provisioned_mounts'], list)
    mnt = PROVISIONING_OUTPUT['provisioned_mounts'][0]
    assert mnt['name'] == '/mnt/photos'
    assert mnt['src'].endswith('amazonaws.com:/')


def test_resources_terminated():
    assert 'terminated_volumes' in PROVISIONING_OUTPUT
    res = list([
        tv for tv in PROVISIONING_OUTPUT['terminated_volumes'] if tv['changed']
    ])

    assert len(res) == 1


def test_stackmate_state_generated():
    assert 'stackmate_state' in PROVISIONING_OUTPUT
    assert isinstance(PROVISIONING_OUTPUT['stackmate_state'], list)
    assert PROVISIONING_OUTPUT['stackmate_state']
