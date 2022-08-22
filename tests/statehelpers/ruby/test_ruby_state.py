# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915,E0401,E0611
import json
import types
from stackmate.ansible.roles.ruby.filter_plugins.helpers \
    import FilterModule, get_stackmate_ruby_state

OUTPUT_FILE = 'stackmate/ansible/roles/ruby/' \
            + 'molecule/default/' \
            + 'provisioning-output.json'

PROVISION_VARS = None
with open(OUTPUT_FILE) as output:
    PROVISION_VARS = json.load(output)


def test_filter_exported():
    filters = FilterModule().filters()
    assert 'get_stackmate_ruby_state' in filters
    assert isinstance(filters['get_stackmate_ruby_state'], types.FunctionType)


def test_get_stackmate_ruby_state():
    state = get_stackmate_ruby_state(PROVISION_VARS)
    assert isinstance(state, dict)
    assert state['role'] == 'ruby'
    assert isinstance(state['resources'], list)
    assert isinstance(state['resources'][0], dict)

    resource = state['resources'][0]
    assert resource['group'] == 'application'
    assert resource['id'] == 'dependency-application-server-ruby'
    assert resource['created_at']

    provisions = resource['provision_params']
    assert sorted(list(provisions.keys())) == sorted(['version'])
    assert provisions['version'] == '2.7.2'
