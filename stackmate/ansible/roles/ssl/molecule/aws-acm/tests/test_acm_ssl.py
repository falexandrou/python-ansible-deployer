# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915
import json

PROVISIONING_OUTPUT = None
with open('./provisioning-output.json') as output:
    PROVISIONING_OUTPUT = json.load(output)


def test_certificates_provisioned():
    assert 'provisions_result' in PROVISIONING_OUTPUT
    assert PROVISIONING_OUTPUT['provisions_result']
    # There are 2 ssl certificates, one of them is for a cloudfront
    # distribution both of them contain the same domain names
    # BUT different regions
    assert len(PROVISIONING_OUTPUT['provisions_result']) == 2

    # try and locate the result we're interested in
    # (there's a permanent ssl certificate as well)
    result = None
    for res in PROVISIONING_OUTPUT['provisions_result']:
        domain = res['result']['domain']
        alt_names = res['result']['alternative_names']

        if 'cdn.ezploy.eu' in alt_names and domain == 'ezploy.eu':
            result = res['result']
            break

    assert result
    expected_alt_names = sorted(['cdn.ezploy.eu', 'ezploy.eu'])
    assert sorted(result['alternative_names']) == expected_alt_names
    assert result['domain'] == 'ezploy.eu'
    assert result['dns_validation_records']
    recs = result['dns_validation_records']
    assert all(rec['validation_status'] == 'SUCCESS' for rec in recs)
    assert result['arn'].startswith('arn:aws:acm:')
    assert result['status'] == 'ISSUED'
    assert result['is_verified']


def test_certificates_terminated():
    assert 'terminations_results' in PROVISIONING_OUTPUT
    assert PROVISIONING_OUTPUT['terminations_results']
    assert len(PROVISIONING_OUTPUT['terminations_results']) == 1
    termination = PROVISIONING_OUTPUT['terminations_results'][0]
    assert termination['result']
    assert termination['result']['arn'].startswith('arn:aws:acm:eu-central-1')


def test_stackmate_state_generated():
    assert 'stackmate_state' in PROVISIONING_OUTPUT
    assert isinstance(PROVISIONING_OUTPUT['stackmate_state'], list)
    assert PROVISIONING_OUTPUT['stackmate_state']
