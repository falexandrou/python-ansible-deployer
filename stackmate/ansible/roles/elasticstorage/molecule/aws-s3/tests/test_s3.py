# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915
import json

PROVISIONING_OUTPUT = None
with open('./provisioning-output.json') as output:
    PROVISIONING_OUTPUT = json.load(output)

CFID = 'arn:aws:iam::cloudfront:user/CloudFront Origin Access Identity'


def is_accessible_by_all(bucket):
    statement = bucket['policy']['Statement']
    return any(
        (s['Effect'] == 'Allow' and s['Principal'] == '*' for s in statement)
    )


def is_accessible_by_cloudfront(bucket):
    statement = bucket['policy']['Statement']

    for stm in statement:
        if not stm['Effect'] == 'Allow':
            continue

        if not isinstance(stm['Principal'], dict):
            continue

        if CFID in stm['Principal']['AWS']:
            return True

    return False


def is_accessible_by_user(bucket, arn):
    statement = bucket['policy']['Statement']

    for stm in statement:
        if not stm['Effect'] == 'Allow':
            continue

        if not isinstance(stm['Principal'], dict):
            continue

        if arn == stm['Principal']['AWS']:
            return True

    return False


def test_user_created():
    assert 'storage_user' in PROVISIONING_OUTPUT
    assert PROVISIONING_OUTPUT['storage_user']
    # figure out why this crashes in circle ci
    # assert 'user_meta' in user
    # assert user['user_meta']
    # assert user['user_meta']['created_user']
    # username = user['user_meta']['created_user']['user_name']
    # assert username == 'stackmatestorage-ezploy-eu'

    assert 'iam_user' in PROVISIONING_OUTPUT
    assert PROVISIONING_OUTPUT['iam_user']
    # iam_user = PROVISIONING_OUTPUT['iam_user']
    # assert iam_user['result']['UserName'] == 'stackmatestorage-ezploy-eu'


def test_s3_buckets():
    # make sure all buckets have been created
    assert 'elasticstorage_bucket_results' in PROVISIONING_OUTPUT
    results = PROVISIONING_OUTPUT['elasticstorage_bucket_results']
    user_arn = PROVISIONING_OUTPUT['iam_user']['result']['Arn']

    buckets = {r['name']: r for r in results}

    bucket_names = list(buckets.keys())

    expected_buckets = [
        'stackmate-someprivatebucket',
        'stackmate-onepublicbucket',
        'stackmate-someprivatebucket-with-cdn',
        'stackmate-someprivatebucket-with-custom-cdn-alias',
        'cdn.ezploy.eu',
        'ezploy.eu',
        'www.ezploy.eu',
    ]

    assert bucket_names == expected_buckets

    # check buckets and their visibility one by one
    private = buckets['stackmate-someprivatebucket']
    assert is_accessible_by_user(private, user_arn)
    assert not is_accessible_by_all(private)
    assert not is_accessible_by_cloudfront(private)

    public = buckets['stackmate-onepublicbucket']
    assert is_accessible_by_all(public)
    assert is_accessible_by_user(public, user_arn)
    assert not is_accessible_by_cloudfront(public)

    cdn_enabled_buckets = [
        'stackmate-someprivatebucket-with-cdn',
        'stackmate-someprivatebucket-with-custom-cdn-alias',
        'cdn.ezploy.eu',
        'ezploy.eu',
        'www.ezploy.eu',
    ]

    for bucket_name in cdn_enabled_buckets:
        bucket = buckets[bucket_name]
        assert not is_accessible_by_all(bucket)
        assert is_accessible_by_user(bucket, user_arn)
        assert is_accessible_by_cloudfront(bucket)


def test_stackmate_state_generated():
    assert 'stackmate_state' in PROVISIONING_OUTPUT
    assert isinstance(PROVISIONING_OUTPUT['stackmate_state'], list)


def test_stackmate_credentials_generated():
    assert 'stackmate_generated_credentials' in PROVISIONING_OUTPUT
    assert isinstance(
        PROVISIONING_OUTPUT['stackmate_generated_credentials'], list)
    creds = PROVISIONING_OUTPUT['stackmate_generated_credentials'][0]

    assert 'elasticstorage' in creds
    assert isinstance(creds['elasticstorage'], dict)
    assert 'iam' in creds['elasticstorage']
    assert isinstance(creds['elasticstorage']['iam'], dict)
    assert creds['elasticstorage']['iam']['access_key_id']
    assert creds['elasticstorage']['iam']['secret_access_key']
