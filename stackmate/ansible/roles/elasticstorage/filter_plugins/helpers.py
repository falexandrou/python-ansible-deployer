"""Filters for roles that create elasticstorage buckets"""
# -*- coding: utf-8 -*-
import re
from datetime import datetime

def is_cdn_enabled(item):
    """Returns whether there should be a CDN in front of the bucket"""
    params = item.get('provision_params', {})
    return params.get('cdn') or params.get('website') or params.get('domain') or False


def is_public_bucket(item):
    """Returns whether the bucket is public"""
    params = item.get('provision_params', {})
    return params.get('public') or is_cdn_enabled(item)


def s3_bucket_url(bucket, website=False, region=None):
    """Returns the S3 bucket url"""
    if website and region:
        return '{}.s3-website.{}.amazonaws.com'.format(bucket, region)

    return '{}.s3.amazonaws.com'.format(bucket)


def s3_bucket_name(item):
    """Returns the S3 bucket name"""
    params = item.get('provision_params', {})

    if params.get('website') and params.get('domain'):
        return params['domain']

    return params['name']


def s3_website_domains(item):
    """Returns the domains to be used as the website TLD"""
    if not is_website(item):
        return [], False

    params = item.get('provision_params', {})
    domain = params['domain']

    is_tld = len(domain.split('.')) == 2

    domains = [domain]

    if is_tld:
        domains.append('www.{}'.format(domain))

    primary = next((c for c in domains if c.startswith('www')), domains[0])
    return domains, primary

def is_website(item):
    """Returns whether the item is a website"""
    params = item.get('provision_params', {})
    return is_cdn_enabled(item) and params.get('website')


def s3_website_buckets(item):
    """Returns the configuration regarding the s3 bucket websites"""
    params = item.get('provision_params', {})

    domains, primary = s3_website_domains(item)
    configs = []

    for domain in domains:
        if domain == primary:
            configs.append({
                'domain': domain,
                'directory_index': params.get('directory_index', 'index.html'),
                'error_page': params.get('error_page', 'error.html'),
                'is_primary': True,
            })
        else:
            configs.append({
                'domain': domain,
                'redirect_to': primary,
                'is_primary': False,
            })

    return configs


def filter_primary_buckets(buckets, is_primary=True):
    """Filters the buckets based on whether they're primary or not"""
    return list([
        bucket for bucket in buckets if bucket.get('is_primary') == is_primary
    ])


def s3_dns_records(item):
    """Extracts the cname records from cloudfront distributions"""
    records = []
    domains, primary = s3_website_domains(item)
    region = item.get('provision_params', {}).get('region')

    for domain in domains:
        # primary domain will be handled by the cloudfront distribution
        if primary == domain:
            continue

        records.append({
            'record': domain,
            'value': s3_bucket_url(domain, website=True, region=region),
        })

    return records

def get_cdn_provision_params(item, origin_access_identity_id=None):
    """Returns the list of provision params to use when deploying a CDN for the bucket"""
    params = item.get('provision_params', {})
    provisions = []
    origin = {}

    s3_origin_config = {}
    if origin_access_identity_id:
        s3_origin_config = {
            's3_origin_config': {
                'origin_access_identity': 'origin-access-identity/cloudfront/{}'.format(
                    origin_access_identity_id
                ),
            },
        }

    if is_website(item):
        domains, primary = s3_website_domains(item)

        for domain in domains:
            if domain != primary:
                continue

            origin = {
                'id': 'S3-{}'.format(domain),
                'domain': s3_bucket_url(domain),
                'aliases': [domain],
            }

            if origin_access_identity_id:
                origin.update(s3_origin_config)

            provisions.append({
                'provision_params': {
                    'name': 's3-{domain}'.format(domain=domain),
                    'root_object': params.get('directory_index'),
                    'origins': [origin],
                },
            })
    else:
        origin = {
            'id': 'S3-{}'.format(params.get('name')),
            'path': '',
            'domain': s3_bucket_url(params.get('name')),
            'aliases': [params['domain']] if params.get('domain') else [],
        }

        if origin_access_identity_id:
            origin.update(s3_origin_config)

        provisions.append({
            'id': 'utility-s3-cdn-{name}'.format(name=params.get('name')),
            'provision_params': {
                'name': 's3-{name}'.format(name=params.get('name')),
                'origins': [origin],
            },
        })

    return provisions


def expand_cors_domains(domains):
    """Expand plain domains to HTTP and HTTPS origins"""
    origins = []

    for domain in domains:
        origins.append('http://{}'.format(domain))
        origins.append('https://{}'.format(domain))

    return origins


def get_storage_username(prefix: str, domain: str):
    """Returns the username to be used as the storage user"""
    return '{prefix}-{suffix}'.format(
        prefix=prefix, suffix=re.sub(r'([^\w]+)', '-', domain))


def iam_policy_name(domain: str) -> str:
    """Provides the name to use in the IAM policy"""
    return 'iam-storage-policy-{}'.format(re.sub(r'([^\w0-9\-])+', '-', domain))


def get_stackmate_aws_elasticstorage_state(variables):
    """
    Returns the state to be used in Stackmate
    """
    resources = []
    rolename = 'elasticstorage'
    provisionables = variables['elasticstorage_provision_items']
    results = variables['elasticstorage_bucket_results']

    for item in provisionables:
        params = item['provision_params']
        res = next((r for r in results if r['tags']['Name'] == params['name']), {})
        generated_creds = variables.get('stackmate_generated_credentials', [])
        creds = generated_creds[0] if generated_creds else {}
        iam_creds = creds.get('elasticstorage', {}).get('iam', {})

        resources.append({
            'id': item['id'],
            'created_at': str(datetime.now()),
            'group': None,
            'provision_params': params,
            'result': res,
            'output': {
                'resource_id': params['name'],
                'ip': None,
                'host': s3_bucket_url(params['name'],
                                      website=params.get('website', False),
                                      region=params.get('region')),
                'port': None,
                'nodes': [],
                'username': iam_creds.get('access_key_id'),
                'password': iam_creds.get('secret_access_key'),
                'root_username': iam_creds.get('user_name'),
                'root_password': iam_creds.get('secret_access_key'),
            }
        })

    return dict(
        role=rolename,
        resources=resources)


class FilterModule:
    """Filters used in the cdn role"""
    # pylint: disable=too-few-public-methods,no-self-use
    def filters(self):
        """Filters to be used in the role"""
        return {
            'is_website': is_website,
            's3_dns_records': s3_dns_records,
            's3_bucket_name': s3_bucket_name,
            'iam_policy_name': iam_policy_name,
            'is_cdn_enabled': is_cdn_enabled,
            'is_public_bucket': is_public_bucket,
            's3_website_buckets': s3_website_buckets,
            'expand_cors_domains': expand_cors_domains,
            'get_storage_username': get_storage_username,
            'filter_primary_buckets': filter_primary_buckets,
            'get_cdn_provision_params': get_cdn_provision_params,
            'get_stackmate_aws_elasticstorage_state': get_stackmate_aws_elasticstorage_state,
        }
