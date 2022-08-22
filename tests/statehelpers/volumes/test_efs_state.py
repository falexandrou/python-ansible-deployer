# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915,E0401,E0611
import json
import types
from stackmate.ansible.roles.volumes.filter_plugins.helpers \
    import FilterModule, get_stackmate_aws_helpers_state

OUTPUT_FILE = 'stackmate/ansible/roles/volumes/' \
            + 'molecule/aws-efs/' \
            + 'provisioning-output.json'

PROVISION_VARS = None
with open(OUTPUT_FILE) as output:
    PROVISION_VARS = json.load(output)


def test_filter_exported():
    filters = FilterModule().filters()
    assert 'get_stackmate_aws_helpers_state' in filters
    assert isinstance(filters['get_stackmate_aws_helpers_state'], types.FunctionType)


def test_get_stackmate_aws_helpers_state():
    state = get_stackmate_aws_helpers_state(PROVISION_VARS)
    assert isinstance(state, dict)
    assert state['role'] == 'volumes'
    assert 'resources' in state
    assert state['resources']

    for res in state['resources']:
        assert sorted(list(res.keys())) == sorted([
            'created_at', 'group', 'id', 'output',
            'provision_params', 'result',
        ])

        assert not res['group']
        assert res['id'].startswith('service-volumes-')
        assert isinstance(res['result'], dict)
        assert res['result']['file_system_id'].startswith('fs-')
        assert res['output']['host'].endswith(
            'efs.eu-central-1.amazonaws.com:/')
        # redis does not provide a configuration endpoint
        assert res['output']['resource_id'] == res['result']['file_system_id']
        assert not res['output']['ip']
        assert not res['output']['port']
        assert not res['output']['nodes']
