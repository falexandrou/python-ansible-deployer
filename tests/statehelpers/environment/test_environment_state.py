# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915,E0401,E0611
import json
import types
from stackmate.ansible.roles.environment.filter_plugins.helpers \
    import FilterModule, get_stackmate_envs_state

OUTPUT_FILE = 'stackmate/ansible/roles/environment/' \
            + 'molecule/default/' \
            + 'provisioning-output.json'

PROVISION_VARS = None
with open(OUTPUT_FILE) as output:
    PROVISION_VARS = json.load(output)


def test_filter_exported():
    filters = FilterModule().filters()
    assert 'get_stackmate_envs_state' in filters
    assert isinstance(filters['get_stackmate_envs_state'], types.FunctionType)


def test_get_stackmate_envs_state():
    state = get_stackmate_envs_state(PROVISION_VARS)
    assert isinstance(state, dict)
    assert state['role'] == 'environment'
    assert 'resources' in state
    assert state['resources']

    for res in state['resources']:
        assert sorted(list(res.keys())) == sorted([
            'created_at', 'group', 'id', 'provision_params',
        ])

        assert res['id'].startswith('utility-environment-')
        assert res['group'] == 'application'
        assert res['created_at']
        assert isinstance(res['provision_params'], dict)
        assert res['provision_params']['export']
        assert res['provision_params']['value']
        assert res['provision_params']['kind'] == 'environment'
