"""Filters for roles that create rds instances"""
# -*- coding: utf-8 -*-
from datetime import datetime

def get_stackmate_aws_ssl_state(variables):
    """
    Returns the state to be used in Stackmate
    """
    resources = []
    rolename = 'ssl'
    results = variables['provisions_result']

    for item in variables['provisions']:
        params = item['provision_params']
        domains = set(params['domains'])

        res = None
        for result in results:
            cert_domains = result['result'].get('alternative_names', [])
            cert_domains.append(result['result']['domain'])

            if domains.issubset(set(cert_domains)):
                res = result
                break

        if not res:
            continue

        resources.append({
            'id': item['id'],
            'created_at': str(datetime.now()),
            'group': item['group'],
            'provision_params': params,
            'result': res,
            'output': {
                'resource_id': res['result']['arn'],
                'ip': None,
                'host': None,
                'port': None,
                'nodes': [],
            }
        })

    return dict(
        role=rolename,
        resources=resources)


class FilterModule:
    """Filters used in the instances role"""
    # pylint: disable=too-few-public-methods

    def filters(self):
        """Filters to be used in the role"""
        # pylint: disable=no-self-use
        return {
            'get_stackmate_aws_ssl_state': get_stackmate_aws_ssl_state,
        }
