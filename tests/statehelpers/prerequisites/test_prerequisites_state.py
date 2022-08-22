# -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915,E0401,E0611
import json
import types
from stackmate.deployables.utility import Utility
from stackmate.ansible.roles.prerequisites.filter_plugins.helpers \
    import FilterModule, get_stackmate_aws_prerequisites_state

OUTPUT_FILE = 'stackmate/ansible/roles/prerequisites/' \
            + 'molecule/aws-vpc/' \
            + 'provisioning-output.json'

PROVISION_VARS = None
with open(OUTPUT_FILE) as prov:
    PROVISION_VARS = json.load(prov)


def test_filter_exported():
    filters = FilterModule().filters()
    assert 'get_stackmate_aws_prerequisites_state' in filters
    assert isinstance(filters['get_stackmate_aws_prerequisites_state'], types.FunctionType)


def test_get_stackmate_aws_prerequisites_state():
    state = get_stackmate_aws_prerequisites_state(PROVISION_VARS)
    util = Utility.factory(kind='prerequisites', provider='aws')
    assert isinstance(state, dict)
    assert 'role' in state
    assert state['role'] == 'prerequisites'
    assert len(state['resources']) == 1
    assert isinstance(state['resources'][0], dict)
    resource = state['resources'][0]
    assert not resource['group']
    assert resource['id'] == util.deployable_id
    assert resource['created_at']

    provisions = resource['provision_params']
    assert sorted(list(provisions.keys())) == sorted(['provider', 'region', 'scm', 'domain'])

    assert provisions['provider'] == 'aws'
    assert provisions['region'] == 'eu-central-1'
    assert provisions['scm'] == 'github'
    assert provisions['domain'] == 'ezploy-test.eu'

    output = resource['output']
    outkeys = [
        'vpc_id', 'vpc_cidr', 'main_vpc_subnet_id', 'alternative_vpc_subnet_id',
        'route_table_id', 'internet_gateway_id', 'default_sg_id',
        'hosted_zone_id', 'ns_records',
    ]
    assert sorted(list(output.keys())) == sorted(outkeys)
    assert all(output[k] for k in outkeys)
