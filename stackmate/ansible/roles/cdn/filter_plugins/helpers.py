"""Filters for roles that create cdn distributions"""
# -*- coding: utf-8 -*-
import re
from datetime import datetime
from ansible.utils.display import Display

AWS_SUFFIX = '.s3.amazonaws.com'
CLOUDFRONT_SUFFIX = '.cloudfront.net'

def get_aliases(origins):
    """Flattens the list of origin aliases"""
    return list({alias for orig in origins for alias in orig.get('aliases', [])})


def cloudfront_origin_id(domain):
    """Forms a cloudfront origin id based on the domain and index"""
    return 'CUSTOM-{}'.format(re.sub(r'([^\w0-9\-])+', '-', domain))


def _covers_domain(domain, cert_domains):
    """Determines whether the SSL certificate covers the domain name"""
    return domain in cert_domains or '*.{domain}'.format(domain=domain) in cert_domains


def certificate_verified_domains(cert):
    """Returns the domains that there is a valid SSL certificate for"""
    domains = [
        cert['domain_name'],
    ]

    if cert.get('subject_alternative_names'):
        domains += cert.get('subject_alternative_names')

    return set(domains)


def cloudfront_default_certificate():
    """Returns the default SSL certificate"""
    Display().warning(
        'No verified SSL certificate could be found, using the default Cloudfront certificate'
    )

    return {
        # default cloudfront certificate
        'cloudfront_default_certificate': True,
        'certificate_source': 'cloudfront',
    }


def cloudfront_distribution_certificate(item, ssl_certificates):
    """Returns the SSL certificate for the distribution"""
    origins = item.get('provision_params', {}).get('origins')

    if not origins:
        # no origins specified, should use the default cloudfront certificate
        return cloudfront_default_certificate()

    domains = get_aliases(origins)
    certificate = None

    for cert in ssl_certificates:
        cert_domains = certificate_verified_domains(cert)
        are_alieses_covered_by_ssl = all(_covers_domain(dom, cert_domains) for dom in domains)

        if are_alieses_covered_by_ssl and cert.get('certificate_arn'):
            certificate = {
                'acm_certificate_arn': cert.get('certificate_arn'),
                'ssl_support_method': 'sni-only',
                'minimum_protocol_version': 'TLSv1.1_2016',
                'certificate': cert.get('certificate_chain'),
                'certificate_source': 'acm',
                'cloudfront_default_certificate': False,
            }

            break

    if not certificate:
        return cloudfront_default_certificate()

    return certificate


def cloudfront_aliases(item, certificates):
    """Returns the alliases for the cdn distribution"""
    certificate = cloudfront_distribution_certificate(item, certificates)

    if certificate and not certificate.get('cloudfront_default_certificate'):
        return get_aliases(item.get('provision_params', {}).get('origins', []))

    return []


def cloudfront_cache_behaviors(item):
    """Cloudfront cache behaviors"""
    origins = cloudfront_origins(item)
    default_behavior = {
        'forwarded_values': {
            'query_string': True,
            'cookies': {'forward': 'all'},
            'headers': ['*'],
        },
        'path_pattern': '*',
        'viewer_protocol_policy': 'redirect-to-https',
        'smooth_streaming': True,
        'compress': True,
        'min_ttl': 0,
        'default_ttl': 600,
        'max_ttl': 7200,
        'field_level_encryption_id': '',
        'allowed_methods': {
            'items': ['GET', 'HEAD'],
            'cached_methods': ['GET', 'HEAD'],
        },
    }

    behaviors = []
    for origin in origins:
        behavior = dict(target_origin_id=origin['id'], **default_behavior)

        if origin['domain_name'].endswith(AWS_SUFFIX):
            behavior['forwarded_values']['headers'] = [
                'Access-Control-Request-Headers',
                'Access-Control-Request-Method',
                'Origin',
            ]

        behaviors.append(behavior)

    return behaviors


def cloudfront_default_cache_behavior(item):
    """Cloudfront default cache_behavior"""
    behaviors = cloudfront_cache_behaviors(item)

    if not behaviors:
        return {}

    keys = [
        'target_origin_id', 'forwarded_values', 'viewer_protocol_policy',
        'min_ttl', 'allowed_methods', 'default_ttl', 'max_ttl', 'compress',
        'field_level_encryption_id',
    ]


    return {key: value for key, value in behaviors[0].items() if key in keys}


def cloudfront_origins(item):
    """Returns the non-default origins for the distribution as a list of dictionaries"""
    origins = item.get('provision_params', {}).get('origins', [])

    if not origins:
        return []

    origin_list = []
    for orig in origins:
        origin_id = orig.get('id')

        if not origin_id:
            origin_id = cloudfront_origin_id(orig.get('domain'))

        origin = {
            'id': origin_id,
            'domain_name': orig.get('domain'),
            'origin_path': orig.get('path', ''),
        }

        if origin['domain_name'].endswith(AWS_SUFFIX):
            s3_origin_config = orig.get('s3_origin_config', {})

            origin.update({
                's3_origin_config': s3_origin_config,
            })

        origin_list.append(origin)

    return origin_list


def cloudfront_dns_records(distro):
    """Extracts the cname records from cloudfront distributions"""
    if not distro:
        return []

    if not distro.get('aliases') or not distro['aliases'].get('items'):
        return []

    return list([{
        'record': record,
        'value': distro['domain_name'],
    } for record in distro['aliases']['items']])


def cloudfront_terminatable_dns_records(item, records):
    """Returns the DNS records (associated with the item) to be terminated"""
    origins = item.get('provision_params', {}).get('origins', [])

    if not records:
        return []

    aliases = []
    for origin in origins:
        aliases += origin.get('aliases', [])

    entries = []
    for recset in records.get('ResourceRecordSets', []):
        # we're only interested in A records
        if recset.get('Type') != 'A':
            continue

        # The records should be an alias
        if not recset.get('AliasTarget'):
            continue

        # the name should be in the aliases
        recname = re.sub(r'(\.)$', '', recset.get('Name'))
        if not recname in aliases:
            continue

        # there should be a value and it should include ".cloudfront.net"
        value = recset['AliasTarget']['DNSName']
        if not value or not CLOUDFRONT_SUFFIX in value:
            continue

        entries.append({
            'record': recname,
            'value': value,
        })

    return entries


def get_stackmate_aws_cdn_state(variables):
    """
    Returns the state to be used in Stackmate
    """
    resources = []
    rolename = 'cdn'
    provisionables = variables['provision_items']

    for res in variables['provision_results']:
        item = None
        name = res['caller_reference']

        for itm in provisionables:
            if itm['provision_params']['name'] == name:
                item = itm
                break

        if not item:
            continue

        resources.append({
            'id': item['id'],
            'created_at': str(datetime.now()),
            'group': None,
            'provision_params': item['provision_params'],
            'result': res,
            'output': {
                'resource_id': res['id'],
                'host': res['domain_name'],
                'ip': None,
                'port': None,
                'nodes': [],
            }
        })

    return dict(
        role=rolename,
        resources=resources)


def extract_cloudfront_domains(created_records):
    """Extracts the cloudfront domains that were created during provisioning"""
    return list([r['rec']['value'] for r in created_records])


class FilterModule:
    """Filters used in the cdn role"""
    # pylint: disable=too-few-public-methods,no-self-use
    def filters(self):
        """Filters to be used in the role"""
        return {
            'cloudfront_aliases': cloudfront_aliases,
            'cloudfront_origins': cloudfront_origins,
            'cloudfront_dns_records': cloudfront_dns_records,
            'cloudfront_cache_behaviors': cloudfront_cache_behaviors,
            'cloudfront_default_cache_behavior': cloudfront_default_cache_behavior,
            'cloudfront_distribution_certificate': cloudfront_distribution_certificate,
            'cloudfront_terminatable_dns_records': cloudfront_terminatable_dns_records,
            'extract_cloudfront_domains': extract_cloudfront_domains,
            'get_stackmate_aws_cdn_state': get_stackmate_aws_cdn_state,
        }
