# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915,E0401,E0611
import json
import types
from stackmate.deployables.utility import Utility
from stackmate.ansible.roles.essentials.filter_plugins.helpers \
    import FilterModule, get_stackmate_essentials_state

OUTPUT_FILE = 'stackmate/ansible/roles/essentials/' \
            + 'molecule/default/' \
            + 'provisioning-output.json'

PROVISION_VARS = None
with open(OUTPUT_FILE) as output:
    PROVISION_VARS = json.load(output)


def test_filter_exported():
    filters = FilterModule().filters()
    assert 'get_stackmate_essentials_state' in filters
    assert isinstance(filters['get_stackmate_essentials_state'], types.FunctionType)


def test_get_stackmate_essentials_state():
    state = get_stackmate_essentials_state(PROVISION_VARS)
    util = Utility.factory(kind='essentials')
    assert isinstance(state, dict)
    assert state['role'] == 'essentials'
    assert len(state['resources']) == 1
    assert isinstance(state['resources'][0], dict)

    resource = state['resources'][0]
    assert resource['group'] == 'provisionables'
    assert resource['id'] == util.deployable_id
    assert resource['created_at']

    provisions = resource['provision_params']
    assert list(provisions.keys()) == []
