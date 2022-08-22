# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915,E0401,E0611
import json
import types
from stackmate.ansible.roles.databases.filter_plugins.helpers \
    import FilterModule, get_stackmate_aws_databases_state

OUTPUT_FILE = 'stackmate/ansible/roles/databases/' \
            + 'molecule/mysql-rds/' \
            + 'provisioning-output.json'

PROVISION_VARS = None
with open(OUTPUT_FILE) as output:
    PROVISION_VARS = json.load(output)


def test_filter_exported():
    filters = FilterModule().filters()
    assert 'get_stackmate_aws_databases_state' in filters
    assert isinstance(filters['get_stackmate_aws_databases_state'], types.FunctionType)


def test_get_stackmate_aws_databases_state():
    state = get_stackmate_aws_databases_state(PROVISION_VARS)
    assert isinstance(state, dict)
    assert state['role'] == 'databases'
    assert 'resources' in state
    assert state['resources']

    for res in state['resources']:
        assert sorted(list(res.keys())) == sorted([
            'created_at', 'group', 'id', 'output',
            'provision_params', 'result',
        ])

        assert res['group'] == 'databases'
        assert res['id'] == 'service-mysql-mysql-database'
        assert isinstance(res['result'], dict)
        assert res['result']['db_instance_identifier'] == 'mysql-database'
        assert res['output']['host'].endswith('eu-central-1.rds.amazonaws.com')
        # redis does not provide a configuration endpoint
        assert not res['output']['nodes']
        assert res['output']['resource_id'] == 'mysql-database'
        assert res['output']['ip'] is None
        assert res['output']['port'] == 3306
        assert res['output']['username'] == 'myuser'
        assert res['output']['password'] == 'mypassword'
        assert res['output']['root_username'] == 'root_db_user'
        assert res['output']['root_password'] == 'root_db_password'
