# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915,E0401,E0611
import json
import types
from stackmate.ansible.roles.routing.filter_plugins.helpers \
    import FilterModule, get_stackmate_aws_routing_state

OUTPUT_FILE = 'stackmate/ansible/roles/routing/' \
            + 'molecule/aws-alb/' \
            + 'provisioning-output.json'

PROVISION_VARS = None
with open(OUTPUT_FILE) as output:
    PROVISION_VARS = json.load(output)


def test_filter_exported():
    filters = FilterModule().filters()
    assert 'get_stackmate_aws_routing_state' in filters
    assert isinstance(filters['get_stackmate_aws_routing_state'], types.FunctionType)


def test_get_stackmate_aws_routing_state():
    state = get_stackmate_aws_routing_state(PROVISION_VARS)
    assert isinstance(state, dict)
    assert state['role'] == 'routing'
    assert 'resources' in state
    assert state['resources']

    for res in state['resources']:
        assert sorted(list(res.keys())) == sorted([
            'created_at', 'group', 'id', 'output',
            'provision_params', 'result',
        ])

        params = res['provision_params']
        alb_name = 'loadbalancer-%s' % params['target_group']

        assert not res['group']
        assert res['id'].startswith('service-routing-')
        assert isinstance(res['result'], dict)
        assert res['result']['load_balancer_name'] == alb_name
        assert res['output']['host'].endswith('eu-central-1.elb.amazonaws.com')
        # redis does not provide a configuration endpoint
        assert res['output']['resource_id'] == res['result']['load_balancer_name']
        assert res['output']['ip'] is None
        assert res['output']['port'] == 80
        assert not res['output']['nodes']
