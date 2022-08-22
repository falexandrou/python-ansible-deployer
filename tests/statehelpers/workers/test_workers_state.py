# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915,E0401,E0611
import json
import types
from stackmate.ansible.roles.workers.filter_plugins.helpers \
    import FilterModule, get_stackmate_workers_state

OUTPUT_FILE = 'stackmate/ansible/roles/workers/' \
            + 'molecule/default/' \
            + 'provisioning-output.json'

PROVISION_VARS = None
with open(OUTPUT_FILE) as output:
    PROVISION_VARS = json.load(output)


def test_filter_exported():
    filters = FilterModule().filters()
    assert 'get_stackmate_workers_state' in filters
    assert isinstance(filters['get_stackmate_workers_state'], types.FunctionType)


def test_get_stackmate_workers_state():
    state = get_stackmate_workers_state(PROVISION_VARS)
    assert isinstance(state, dict)
    assert state['role'] == 'workers'
    assert isinstance(state['resources'], list)
    assert state['resources']

    for res in state['resources']:
        assert res['id'].startswith('dependency-')
        assert res['created_at']
        assert res['group']
        assert res['provision_params']
