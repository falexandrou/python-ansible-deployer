# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915
import json
import pytest

PROVISIONING_OUTPUT = None
with open('./provisioning-output.json') as output:
    PROVISIONING_OUTPUT = json.load(output)


def test_elb_resources_created():
    assert 'provision_results' in PROVISIONING_OUTPUT
    assert len(PROVISIONING_OUTPUT['provision_results']) == 1
    alb = PROVISIONING_OUTPUT['provision_results'][0]
    assert alb['changed']
    assert alb['type'] == 'application'
    assert alb['tags'] == {
        "Application": "load-balancer-production",
        'Environment': 'molecule-test',
        'Group': 'application',
        'Name': 'loadbalancer-application',
    }


def test_elb_resources_terminated():
    assert 'termination_results' in PROVISIONING_OUTPUT
    assert len(PROVISIONING_OUTPUT['termination_results']) == 1
    assert PROVISIONING_OUTPUT['termination_results'][0]['changed']


RECORDSETS = [
    PROVISIONING_OUTPUT['provisioned_dns_records'],
    PROVISIONING_OUTPUT['terminated_dns_records'],
]


@pytest.mark.parametrize('recordset', RECORDSETS)
def test_dns_records_created(recordset):
    recs = [rs['rec'] for rs in recordset]
    domains = list([rec['record'] for rec in recs])
    types = list([rec['record_type'] for rec in recs])
    assert domains == ['ezploy.eu', 'www.ezploy.eu']
    assert types == ['A', 'CNAME']


def test_stackmate_state_generated():
    assert 'stackmate_state' in PROVISIONING_OUTPUT
    assert isinstance(PROVISIONING_OUTPUT['stackmate_state'], list)
