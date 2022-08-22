# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915
import json

PROVISIONING_OUTPUT = None
with open('./provisioning-output.json') as output:
    PROVISIONING_OUTPUT = json.load(output)


def test_sns_topic_registrations():
    assert 'sns_bounces' in PROVISIONING_OUTPUT
    assert PROVISIONING_OUTPUT['sns_bounces'].get('sns_arn') is not None
    assert 'sns_complaints' in PROVISIONING_OUTPUT
    assert PROVISIONING_OUTPUT['sns_complaints'].get('sns_arn') is not None
    assert 'sns_deliveries' in PROVISIONING_OUTPUT
    assert PROVISIONING_OUTPUT['sns_deliveries'].get('sns_arn') is not None


def test_user_created():
    assert 'ses_user' in PROVISIONING_OUTPUT
    assert 'user_meta' in PROVISIONING_OUTPUT['ses_user']
    assert 'access_keys' in PROVISIONING_OUTPUT['ses_user']['user_meta']

    meta = PROVISIONING_OUTPUT['ses_user']['user_meta']['access_keys'][0]
    assert isinstance(meta, dict)
    assert meta.get('secret_access_key')
    uname = 'stackmatemailer-permanent-molecule-test-myappis-live'
    assert meta.get('user_name') == uname

    # test that the policy has been applied
    assert 'iam_user_policy' in PROVISIONING_OUTPUT
    policy = PROVISIONING_OUTPUT['iam_user_policy']
    assert policy['user_name'] == uname
    assert policy['policies'] == [
        'iam-policy-permanent-molecule-test-myappis-live']


def test_ses_domain_created():
    assert 'ses_domain' in PROVISIONING_OUTPUT
    assert PROVISIONING_OUTPUT['ses_domain'].get('identity')
    identity = PROVISIONING_OUTPUT['ses_domain']['identity']
    assert identity == 'permanent-molecule-test.myappis.live'


def test_ses_emails_created():
    assert 'ses_emails' in PROVISIONING_OUTPUT
    results = PROVISIONING_OUTPUT['ses_emails']['results']
    assert list(e['identity'] for e in results) == [
        'fotis@permanent-molecule-test.myappis.live',
    ]


def test_verification_records():
    assert 'dkim_records' in PROVISIONING_OUTPUT
    assert PROVISIONING_OUTPUT['dkim_records']
    assert 'result' in PROVISIONING_OUTPUT['dkim_records']
    assert PROVISIONING_OUTPUT['dkim_records']['result']
    assert 'dkim_verified' in PROVISIONING_OUTPUT['dkim_records']['result']
    assert 'is_verified' in PROVISIONING_OUTPUT['dkim_records']['result']
    identity = PROVISIONING_OUTPUT['dkim_records']['result']['identity']
    assert identity == 'permanent-molecule-test.myappis.live'


def test_smtp_credentials():
    assert 'smtp_credentials' in PROVISIONING_OUTPUT
    keys = list(PROVISIONING_OUTPUT['smtp_credentials']['result'].keys())
    assert sorted(keys) == sorted([
        'password', 'port', 'server', 'username',
    ])


def test_stackmate_state_generated():
    assert 'stackmate_state' in PROVISIONING_OUTPUT
    assert isinstance(PROVISIONING_OUTPUT['stackmate_state'], list)


def test_stackmate_credentials_generated():
    assert 'stackmate_generated_credentials' in PROVISIONING_OUTPUT
    assert isinstance(
        PROVISIONING_OUTPUT['stackmate_generated_credentials'], list)

    creds = PROVISIONING_OUTPUT['stackmate_generated_credentials'][0]

    assert 'mailer' in creds
    assert isinstance(creds['mailer'], dict)

    assert 'iam' in creds['mailer']
    assert isinstance(creds['mailer']['iam'], dict)
    iam = creds['mailer']['iam']
    assert iam['access_key_id']
    assert iam['secret_access_key']

    assert 'smtp' in creds['mailer']
    assert isinstance(creds['mailer']['smtp'], dict)
    smtp = creds['mailer']['smtp']
    assert smtp['username']
    assert smtp['password']
    assert smtp['port'] == 587
    assert smtp['server'] == 'email-smtp.eu-central-1.amazonaws.com'


def test_stackmate_user_actions_created():
    assert 'stackmate_user_action' in PROVISIONING_OUTPUT
    assert isinstance(PROVISIONING_OUTPUT['stackmate_user_action'], list)
    assert PROVISIONING_OUTPUT['stackmate_user_action']
    action = PROVISIONING_OUTPUT['stackmate_user_action'][0]
    assert action['key'] == 'domain_validate_email'
    assert isinstance(action['value'], list)
    assert 'fotis@permanent-molecule-test.myappis.live' in action['value']
