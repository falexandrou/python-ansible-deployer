"""Filters for roles that create cdn distributions"""
# -*- coding: utf-8 -*-
from datetime import datetime

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


def elb_domains(item):
    """Returns the domains we're registering the ELB for"""
    params = item.get('provision_params', {})

    if not params.get('domain'):
        return []

    domains = [
        params['domain'],
    ]

    # if the domain is a top level one, add an alias for the www
    if len(params['domain'].split('.')) == 2:
        domains.append('www.{}'.format(params['domain']))

    return domains


def elb_certificate_arns(item, ssl_certificates):
    """Returns the SSL certificate for the distribution"""
    certificates = []
    domains = elb_domains(item)

    for cert in ssl_certificates:
        cert_domains = certificate_verified_domains(cert)
        are_alieses_covered_by_ssl = all(_covers_domain(dom, cert_domains) for dom in domains)

        if are_alieses_covered_by_ssl and cert.get('certificate_arn'):
            certificates.append({
                'CertificateArn': cert.get('certificate_arn'),
            })

    return certificates


def elb_target_group_name(item, prefix):
    """Returns the elb target group name"""
    return '{prefix}-{group}'.format(
        prefix=prefix,
        group=item.get('provision_params', {}).get('target_group', 'generic'))


def elb_alb_name(item, prefix):
    """Returns the elb application load balancer name"""
    return '{prefix}-{group}'.format(
        prefix=prefix,
        group=item.get('provision_params', {}).get('target_group', 'generic'))


def elb_alb_dns_records(item, alb):
    """Returns the DNS records to be created for the alb"""
    primary_domain = item.get('provision_params', {}).get('domain')

    if not primary_domain:
        return []

    records = []
    domains = elb_domains(item)
    for domain in domains:
        if domain == primary_domain:
            records.append({
                'record': primary_domain,
                'record_type': 'A',
                'value': alb['dns_name'],
                'is_alias': True,
                'hosted_zone_id': alb['canonical_hosted_zone_id'],
            })
        else:
            records.append({
                'record': domain,
                'record_type': 'CNAME',
                'value': primary_domain,
                'is_alias': False,
                'hosted_zone_id': None,
            })

    return records


def get_stackmate_aws_routing_state(variables):
    """
    Returns the state to be used in Stackmate
    """
    resources = []
    rolename = 'routing'

    for item in variables['provision_items']:
        params = item['provision_params']
        res = {}

        # look for the load balancer in the provisioning results
        for alb in variables['provision_results']:
            if params['target_group'] == alb['tags']['Group']:
                res = alb
                break

        # result not found
        if not res:
            continue

        resources.append({
            'id': item['id'],
            'created_at': str(datetime.now()),
            'group': None,
            'provision_params': params,
            'result': res,
            'output': {
                'resource_id': res['load_balancer_name'],
                'ip': None,
                'host': res['dns_name'],
                'port': params['target_port'],
                'nodes': [],
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
            'elb_domains': elb_domains,
            'elb_target_group_name': elb_target_group_name,
            'elb_alb_name': elb_alb_name,
            'elb_alb_dns_records': elb_alb_dns_records,
            'elb_certificate_arns': elb_certificate_arns,
            'get_stackmate_aws_routing_state': get_stackmate_aws_routing_state,
        }
