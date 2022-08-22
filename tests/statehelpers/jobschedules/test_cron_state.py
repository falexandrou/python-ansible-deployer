# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915,E0401,E0611
import json
import types
from stackmate.ansible.roles.jobschedules.filter_plugins.helpers \
    import FilterModule, get_stackmate_jobschedules_state

OUTPUT_FILE = 'stackmate/ansible/roles/jobschedules/' \
            + 'molecule/default/' \
            + 'provisioning-output.json'

PROVISION_VARS = None
with open(OUTPUT_FILE) as output:
    PROVISION_VARS = json.load(output)


def test_filter_exported():
    filters = FilterModule().filters()
    assert 'get_stackmate_jobschedules_state' in filters
    assert isinstance(filters['get_stackmate_jobschedules_state'], types.FunctionType)


def test_get_stackmate_jobschedules_state():
    state = get_stackmate_jobschedules_state(PROVISION_VARS)
    assert isinstance(state, dict)
    assert state['role'] == 'jobschedules'
    assert 'resources' in state
    assert state['resources']

    for res in state['resources']:
        assert sorted(list(res.keys())) == sorted([
            'created_at', 'group', 'id', 'output',
            'provision_params', 'result',
        ])

        assert res['group'] == 'application'
        assert res['id']
        assert res['id'].startswith('utility-jobschedules-')
        assert not res['result']
        assert not res['output']
