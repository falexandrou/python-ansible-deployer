"""Filters for roles that create rds instances"""
# -*- coding: utf-8 -*-
from datetime import datetime

def route53_ns_records(result):
    """Returns the NS records for a hosted zone in Route53"""
    recordsets = result.get('ResourceRecordSets', [])

    if not recordsets:
        return []

    nameservers = []
    for recset in recordsets:
        if not recset.get('Type') or recset['Type'] != 'NS':
            continue

        nameservers += list([record['Value'] for record in recset.get('ResourceRecords')])

    return nameservers


def get_stackmate_aws_prerequisites_state(variables):
    """Returns the state to be used in Stackmate"""
    keys = ['provider', 'region', 'scm', 'domain']
    provision_params = {k: variables[k] for k in keys}

    output_keys = [
        'vpc_id', 'vpc_cidr', 'main_vpc_subnet_id', 'alternative_vpc_subnet_id',
        'route_table_id', 'internet_gateway_id', 'hosted_zone_id', 'ns_records',
        'default_sg_id',
    ]

    output = {k: variables[k] for k in output_keys}

    return dict(
        role='prerequisites',
        resources=[{
            'id': 'utility-prerequisites',
            'created_at': str(datetime.now()),
            'group': None,
            'provision_params': provision_params,
            'result': None,
            'output': output,
        }]
    )


def extract_ns_records(results):
    """Extracts the NS records from a result set"""
    ns_recordsets = [
        r.get('ResourceRecords', []) for r in results.get('ResourceRecordSets', [])
        if r.get('Type') == 'NS'
    ]

    return sorted(list([e.get('Value') for r in ns_recordsets for e in r]))


def get_top_level_domain(domain, preview_domain):
    """Returns the top level domain to use"""
    # preview domains should be returned as they are
    if domain.endswith(preview_domain):
        return domain

    return '.'.join(domain.split('.')[-2:])


class FilterModule:
    """Filters used in the instances role"""
    # pylint: disable=too-few-public-methods

    def filters(self):
        """Filters to be used in the role"""
        # pylint: disable=no-self-use
        return {
            'extract_ns_records': extract_ns_records,
            'route53_ns_records': route53_ns_records,
            'get_top_level_domain': get_top_level_domain,
            'get_stackmate_aws_prerequisites_state': get_stackmate_aws_prerequisites_state,
        }
