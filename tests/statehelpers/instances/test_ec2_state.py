# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915,E0401,E0611
import json
import types
from stackmate.ansible.roles.instances.filter_plugins.helpers \
    import FilterModule, get_stackmate_aws_instances_state

OUTPUT_FILE = 'stackmate/ansible/roles/instances/' \
            + 'molecule/aws-ec2/' \
            + 'provisioning-output.json'

PROVISION_VARS = None
with open(OUTPUT_FILE) as output:
    PROVISION_VARS = json.load(output)


def test_filter_exported():
    filters = FilterModule().filters()
    assert 'get_stackmate_aws_instances_state' in filters
    assert isinstance(filters['get_stackmate_aws_instances_state'], types.FunctionType)


def test_get_stackmate_aws_instances_state():
    state = get_stackmate_aws_instances_state(PROVISION_VARS)
    assert isinstance(state, dict)
    assert state['role'] == 'instances'
    assert 'resources' in state
    assert state['resources']

    for res in state['resources']:
        assert sorted(list(res.keys())) == sorted([
            'created_at', 'group', 'id', 'output',
            'provision_params', 'result',
        ])

        assert res['group'] == 'application'
        assert res['id'] == 'service-application-application-server'
        assert isinstance(res['result'], list)
        assert res['result']
        assert res['result'][0]['instance_id'].startswith('i-')
        assert res['output']
        assert set(res['output'].keys()) == set([
            'resource_id', 'host', 'ip', 'port', 'nodes',
        ])
        assert len(res['output']['nodes']) == 2

        for node in res['output']['nodes']:
            assert isinstance(node, dict)
            assert set(node.keys()) == set(['host', 'ip', 'name', 'resource_id', 'port'])
            assert node['host']
            assert node['host'].endswith('eu-central-1.compute.amazonaws.com')
            assert node['host'].startswith('ec2-')
            assert node['resource_id'].startswith('i-')
            assert node['ip']
            assert node['port'] is None
