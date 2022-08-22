# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915
import json

PROVISIONING_OUTPUT = None
with open('./provisioning-output.json') as output:
    PROVISIONING_OUTPUT = json.load(output)


def test_vars_registered():
    # the variables should be registered
    variables = [
        'vpc_id', 'vpc_cidr', 'main_vpc_subnet_id', 'ns_records',
        'route_table_id', 'internet_gateway_id', 'alternative_vpc_subnet_id',
    ]

    for var in variables:
        assert var in PROVISIONING_OUTPUT
        assert PROVISIONING_OUTPUT[var]

    # we should have NS records in the varaibles
    assert isinstance(PROVISIONING_OUTPUT['ns_records'], list)
    assert len(PROVISIONING_OUTPUT['ns_records']) == 4

    # we shouldn't have stackmate hosted zones
    assert PROVISIONING_OUTPUT['stackmate_hosted_entries']

    # we should have a set of user actions for the NS records in the list
    assert 'stackmate_user_action' in PROVISIONING_OUTPUT
    assert isinstance(PROVISIONING_OUTPUT['stackmate_user_action'], list)
    assert PROVISIONING_OUTPUT['stackmate_user_action']
    pending_action = PROVISIONING_OUTPUT['stackmate_user_action'][0]

    assert pending_action
    assert pending_action['key'] == 'ns_records'
    assert isinstance(pending_action['value'], list)
    assert len(pending_action['value']) == 4

    records = PROVISIONING_OUTPUT['ns_records']
    assert records
    assert pending_action['value'] == records


def test_stackmate_state_generated():
    assert 'stackmate_state' in PROVISIONING_OUTPUT
    assert isinstance(PROVISIONING_OUTPUT['stackmate_state'], list)
