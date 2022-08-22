# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915,E0401,E0611
import json
import types
from stackmate.ansible.roles.elasticstorage.filter_plugins.helpers \
    import FilterModule, get_stackmate_aws_elasticstorage_state

OUTPUT_FILE = 'stackmate/ansible/roles/elasticstorage/' \
            + 'molecule/aws-s3/' \
            + 'provisioning-output.json'


PROVISION_VARS = None
with open(OUTPUT_FILE) as output:
    PROVISION_VARS = json.load(output)


def test_filter_exported():
    filters = FilterModule().filters()
    assert 'get_stackmate_aws_elasticstorage_state' in filters
    assert isinstance(filters['get_stackmate_aws_elasticstorage_state'], types.FunctionType)


def test_get_stackmate_aws_elasticstorage_state():
    state = get_stackmate_aws_elasticstorage_state(PROVISION_VARS)
    assert isinstance(state, dict)
    assert state['role'] == 'elasticstorage'
    assert 'resources' in state
    assert state['resources']

    for res in state['resources']:
        assert sorted(list(res.keys())) == sorted([
            'created_at', 'group', 'id', 'output',
            'provision_params', 'result',
        ])

        assert not res['group']
        assert res['id'].startswith('service-elasticstorage-')
        assert isinstance(res['result'], dict)

        assert res['output']['host'].endswith('amazonaws.com')
        region = res['provision_params']['region']
        assert region == 'eu-central-1'

        if res['provision_params'].get('website'):
            assert res['result']['name'] == res['provision_params']['domain']
            assert res['output']['host'].endswith('.s3-website.{}.amazonaws.com'.format(region))
        else:
            assert res['result']['name'] == res['provision_params']['name']
            assert res['output']['host'].endswith('s3.amazonaws.com')

        # redis does not provide a configuration endpoint
        assert res['output']['resource_id'] == res['provision_params']['name']
        assert res['output']['ip'] is None
        assert res['output']['port'] is None
