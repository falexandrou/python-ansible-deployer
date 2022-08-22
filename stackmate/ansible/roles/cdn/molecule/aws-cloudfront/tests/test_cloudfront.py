# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915
import re
import json

PROVISIONING_OUTPUT = None
with open('./provisioning-output.json') as output:
    PROVISIONING_OUTPUT = json.load(output)


def test_generic_registrations():
    assert 'ssl_certificates' in PROVISIONING_OUTPUT
    assert 'dns_records' in PROVISIONING_OUTPUT


def test_distributions_created():
    assert 'created_dns_records' in PROVISIONING_OUTPUT
    assert 'provision_results' in PROVISIONING_OUTPUT
    distros = PROVISIONING_OUTPUT['provision_results']
    assert len(distros) == 2

    provisioned_names = [d['tags']['Name'] for d in distros]

    expected_names = [
        'molecule-test-cdn-with-aliases',
        'molecule-test-cdn-without-aliases',
    ]

    assert provisioned_names == expected_names

    cdns = {
        'molecule-test-cdn-with-aliases': {},
        'molecule-test-cdn-without-aliases': {},
    }

    for distro in distros:
        name = distro['tags']['Name']
        origins = distro['origins']['items']

        cdns[name] = {
            'aliases': distro.get('aliases', {}).get('items', []),
            'domains': [orig['domain_name'] for orig in origins],
            'paths': [orig['origin_path'] for orig in origins],
        }

    # test the provisioned cdns
    provisioned1 = cdns['molecule-test-cdn-with-aliases']
    assert provisioned1['domains'] == ['ezploy.eu']
    assert provisioned1['aliases'] == ['www.ezploy.eu']
    assert provisioned1['paths'] == ['/assets/provisioned1']

    provisioned2 = cdns['molecule-test-cdn-without-aliases']
    assert provisioned2['domains'] == ['ezploy.eu']
    assert provisioned2['aliases'] == []
    assert provisioned2['paths'] == ['/assets/provisioned2']


def test_cdn_terminations():
    assert 'termination_results' in PROVISIONING_OUTPUT
    terminations = PROVISIONING_OUTPUT['termination_results']
    assert len(terminations) == 2


def test_route53_records_created():
    # make sure the route53 records got created
    assert 'created_dns_records' in PROVISIONING_OUTPUT
    records = PROVISIONING_OUTPUT['created_dns_records']

    domains = [r['rec']['record'] for r in records]
    expected_domains = ['www.ezploy.eu']
    assert domains == expected_domains

    values = [r['rec']['value'] for r in records]
    assert all(re.match(r'^([\w0-9]+).cloudfront.net$', val) for val in values)


def test_stackmate_state_generated():
    assert 'stackmate_state' in PROVISIONING_OUTPUT
    assert isinstance(PROVISIONING_OUTPUT['stackmate_state'], list)


def test_stackmate_pending_actions():
    assert 'stackmate_user_action' in PROVISIONING_OUTPUT
    assert isinstance(PROVISIONING_OUTPUT['stackmate_user_action'], list)
    assert PROVISIONING_OUTPUT['stackmate_user_action']

    action = PROVISIONING_OUTPUT['stackmate_user_action'][0]
    assert action['key'] == 'cdn_activations'
    assert isinstance(action['value'], list)
    recs = [
        r['rec']['value'] for r in PROVISIONING_OUTPUT['created_dns_records']
    ]
    assert sorted(action['value']) == sorted(list(recs))
