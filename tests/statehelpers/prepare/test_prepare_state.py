# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915,E0401,E0611
import json
import types
from stackmate.deployables.utility import Utility
from stackmate.ansible.roles.prepare.filter_plugins.helpers \
    import FilterModule, get_stackmate_aws_prepare_state


OUTPUT_FILE = 'stackmate/ansible/roles/prepare/' \
            + 'molecule/default/' \
            + 'provisioning-output.json'

PROVISION_VARS = None
with open(OUTPUT_FILE) as prov:
    PROVISION_VARS = json.load(prov)


def test_filter_exported():
    filters = FilterModule().filters()
    assert 'get_stackmate_aws_prepare_state' in filters
    assert isinstance(filters['get_stackmate_aws_prepare_state'], types.FunctionType)


def test_get_stackmate_aws_prepare_state():
    state = get_stackmate_aws_prepare_state(PROVISION_VARS)
    util = Utility.factory(kind='prepare')

    assert isinstance(state, dict)
    assert 'role' in state
    assert state['role'] == 'prepare'
    assert len(state['resources']) == 1
    assert isinstance(state['resources'][0], dict)
    resource = state['resources'][0]
    assert not resource['group']
    assert resource['id'] == util.deployable_id
    assert resource['created_at']

    provisions = resource['provision_params']
    assert sorted(list(provisions.keys())) == sorted(['repository', 'scm'])

    assert provisions['scm'] == 'github'
    assert provisions['repository']

    output = resource['output']

    outkeys = [
        'deploy_key_id', 'public_key', 'cloud_user_id',
    ]
    assert sorted(list(output.keys())) == sorted(outkeys)
    assert all(output[k] for k in outkeys)
