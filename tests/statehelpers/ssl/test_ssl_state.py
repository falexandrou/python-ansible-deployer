# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915,E0401,E0611
import json
import types
from stackmate.ansible.roles.ssl.filter_plugins.helpers \
    import FilterModule, get_stackmate_aws_ssl_state

OUTPUT_FILE = 'stackmate/ansible/roles/ssl/' \
            + 'molecule/aws-acm/' \
            + 'provisioning-output.json'

PROVISION_VARS = None
with open(OUTPUT_FILE) as output:
    PROVISION_VARS = json.load(output)


def test_filter_exported():
    filters = FilterModule().filters()
    assert 'get_stackmate_aws_ssl_state' in filters
    assert isinstance(filters['get_stackmate_aws_ssl_state'], types.FunctionType)


def test_get_stackmate_aws_ssl_state():
    state = get_stackmate_aws_ssl_state(PROVISION_VARS)
    assert isinstance(state, dict)
    assert state['role'] == 'ssl'
    assert 'resources' in state
    assert state['resources']

    for res in state['resources']:
        assert set(res.keys()) == {
            'created_at', 'group', 'id', 'output',
            'provision_params', 'result',
        }

        assert res['group'] == 'application'
        assert res['id'] == 'utility-ssl'
        assert isinstance(res['result'], dict)
        # redis does not provide a configuration endpoint
        assert res['output']['resource_id'].startswith('arn:aws:acm:')
        assert not res['output']['ip']
        assert not res['output']['port']
        assert not res['output']['nodes']
