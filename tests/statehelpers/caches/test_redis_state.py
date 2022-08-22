# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915,E0401,E0611
import json
import types
from stackmate.ansible.roles.caches.filter_plugins.helpers \
    import FilterModule, get_stackmate_aws_caches_state

OUTPUT_FILE = 'stackmate/ansible/roles/caches/' \
            + 'molecule/aws-redis-elasticache/' \
            + 'provisioning-output.json'

PROVISION_VARS = None
with open(OUTPUT_FILE) as output:
    PROVISION_VARS = json.load(output)


def test_filter_exported():
    filters = FilterModule().filters()
    assert 'get_stackmate_aws_caches_state' in filters
    assert isinstance(filters['get_stackmate_aws_caches_state'], types.FunctionType)


def test_get_stackmate_aws_caches_state():
    state = get_stackmate_aws_caches_state(PROVISION_VARS)
    assert isinstance(state, dict)
    assert state['role'] == 'caches'
    assert 'resources' in state
    assert state['resources']

    for res in state['resources']:
        assert sorted(list(res.keys())) == sorted([
            'created_at', 'group', 'id', 'output',
            'provision_params', 'result',
        ])

        assert res['group'] == 'caches'
        assert res['id'] == 'service-caches-cache-cluster'
        assert isinstance(res['result'], dict)
        assert res['result']['CacheClusterId'] == 'redis-cluster'
        assert res['output']['host'].endswith('euc1.cache.amazonaws.com')
        # redis does not provide a configuration endpoint
        assert res['output']['resource_id'] == 'redis-cluster'
        assert res['output']['ip'] is None
        assert res['output']['port'] == 6379
        assert len(res['output']['nodes']) == 1
        node = res['output']['nodes'][0]
        node = res['output']['nodes'][0]
        assert isinstance(node, dict)
        assert set(node.keys()) == set(['name', 'resource_id', 'ip', 'port', 'host'])
        assert node['host'].endswith('euc1.cache.amazonaws.com')
