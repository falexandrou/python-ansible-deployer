"""Filters for roles that create rds instances"""
# -*- coding: utf-8 -*-
import re
from datetime import datetime

ELASTICACHE_PARAM_GROUPS = {
    'redis': {
        'default': 'redis5.0',
        '5.0.6': 'redis5.0',
        '5.0.5': 'redis5.0',
        '5.0.4': 'redis5.0',
        '5.0.3': 'redis5.0',
        '5.0.0': 'redis5.0',
        '4.0.10': 'redis4.0',
        '3.2.10': 'redis3.0',
        '3.2.6': 'redis3.0',
        '3.2.4': 'redis3.0',
    },
    'memcached': {
        'default': 'memcached1.5',
        '1.5.16': 'memcached1.5',
        '1.5.10': 'memcached1.5',
        '1.4.34': 'memcached1.4',
        '1.4.33': 'memcached1.4',
        '1.4.24': 'memcached1.4',
        '1.4.14': 'memcached1.4',
        '1.4.5': 'memcached1.4',
    },
}


def elasticache_param_group_name(item):
    """Returns the parameter group name to use"""
    params = item.get('provision_params', {})
    version = str(params.get('version', 'default'))

    return 'stackmate-{engine}-{version}'.format(
        engine=params.get('kind'),
        version=re.sub(r'\.', '', version))


def elasticache_param_group_family(item):
    """Get the Elasticache param group family to base the parm group on"""
    params = item.get('provision_params')
    engine = params.get('kind')
    version = str(params.get('version', 'default'))

    return ELASTICACHE_PARAM_GROUPS[engine][version]


def elasticache_extract_instances(result):
    """Extracts the elasticache instances"""
    # params = item.get('provision_params')
    return [{
        'address': res['Endpoint']['Address'],
        'port': res['Endpoint']['Port'],
    } for res in result['CacheNodes']]


def get_installables(item, package_mapping):
    """Returns the list of packages to be installed"""
    params = item.get('provision_params', {})
    kind = params.get('kind')
    version = params.get('version')

    return package_mapping[kind][str(version)]


def get_stackmate_aws_caches_state(variables):
    """
    Returns the state to be used in Stackmate
    """
    resources = []
    rolename = 'caches'
    provisionables = variables['cache_provision_items']

    for res in variables['provision_results']:
        item = None

        for prov in provisionables:
            if prov['provision_params']['name'] == res['CacheClusterId']:
                item = prov
                break

        if item is None:
            continue

        # redis does not provide a configuration endpoint, but memcached does
        endpoint = None
        if res.get('ConfigurationEndpoint', {}):
            endpoint = res.get('ConfigurationEndpoint', {})
        elif res.get('CacheNodes', []):
            endpoint = res['CacheNodes'][0].get('Endpoint')

        if endpoint is None:
            continue

        nodes = []
        for rnode in res.get('CacheNodes', []):
            nodes.append({
                'name': item['provision_params']['name'],
                'resource_id': None,
                'ip': None,
                'port': rnode['Endpoint']['Port'],
                'host': rnode['Endpoint']['Address'],
            })

        resources.append({
            'id': item['id'],
            'created_at': str(datetime.now()),
            'group': item['group'],
            'provision_params': item['provision_params'],
            'result': res,
            'output': {
                'resource_id': res['CacheClusterId'],
                'ip': None,
                'host': endpoint.get('Address'),
                'port': endpoint.get('Port'),
                'nodes': nodes,
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
            'elasticache_param_group_name': elasticache_param_group_name,
            'elasticache_param_group_family': elasticache_param_group_family,
            'elasticache_extract_instances': elasticache_extract_instances,
            'get_installables': get_installables,
            'get_stackmate_aws_caches_state': get_stackmate_aws_caches_state,
        }
