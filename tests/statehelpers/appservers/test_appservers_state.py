# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915,E0401,E0611
import json
import types
from stackmate.ansible.roles.appservers.filter_plugins.helpers \
    import FilterModule, get_stackmate_appservers_state

OUTPUT_FILE = 'stackmate/ansible/roles/' \
            + 'appservers/molecule/default/' \
            + 'provisioning-output.json'

PROVISION_VARS = None

with open(OUTPUT_FILE) as output:
    PROVISION_VARS = json.load(output)


def test_filter_exported():
    filters = FilterModule().filters()
    assert 'get_stackmate_appservers_state' in filters
    assert isinstance(filters['get_stackmate_appservers_state'], types.FunctionType)


def test_get_stackmate_appservers_state():
    state = get_stackmate_appservers_state(PROVISION_VARS)
    assert isinstance(state, dict)
    assert 'role' in state
    assert 'resources' in state
    assert state['resources']

    assert state['role'] == 'appservers'
    assert isinstance(state['resources'], list)
    expected_keys = sorted([
        'created_at',
        'group',
        'id',
        'provision_params',
    ])

    assert all(
        sorted(list(r.keys())) == expected_keys for r in state['resources']
    )

    assert all(r['id'].startswith('dependency-') for r in state['resources'])
    assert all(r['group'] == 'application' for r in state['resources'])
