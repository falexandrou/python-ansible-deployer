"""Filters for roles that create rds instances"""
# -*- coding: utf-8 -*-
import re
from datetime import datetime

PRODUCTION_RDS_ENGINES = {
    'mysql': 'mysql',
    'postgres': 'postgres',
    'postgresql': 'postgres',
    # TODO: enable aurora
    # 'mysql': 'aurora-mysql',
    # 'postgresql': 'aurora-postgresql',
}

RDS_PARAM_GROUPS = {
    'aurora-mysql': {
        'default': 'aurora-mysql5.7',
        '5.7': 'aurora-mysql5.7',
    },
    'aurora-postgresql': {
        'default': 'aurora-postgresql10',
        '9.6': 'aurora-postgresql9.6',
        '10.10': 'aurora-postgresql10',
        '11': 'aurora-postgresql11',
    },
    'mysql': {
        'default': 'mysql5.7',
        '5.7': 'mysql5.7',
    },
    'postgres': {
        'default': 'postgres10',
        '10.10': 'postgres10',
    },
}


def get_installables(provisions, modifications, package_mapping):
    """Returns the list of packages to be installed"""
    entries = provisions if provisions else []
    entries += modifications if modifications else []

    packages = set()

    for param in [entry['provision_params'] for entry in entries]:
        engine = param.get('engine')
        version = param.get('version')

        if not engine or not version:
            continue

        for pkg in package_mapping[engine][str(version)]:
            packages.add(pkg)

    return packages


def rds_extract_instances(results):
    """Extract the instance dictionaries from an ec2_instance result"""
    instances = []
    for entry in results:
        instances.append({
            'address': entry['endpoint']['address'],
            'port': entry['endpoint']['port'],
            'group': entry['tags'].get('Group', 'databases'),
        })

    return instances


def rds_cluster_name(item):
    """Return the cluster name that a group of instances should be located in"""
    params = item.get('provision_params')

    if not params or not params.get('nodes') or params.get('nodes') <= 1:
        return None

    return '{name}-{engine}-cluster'.format(
        name=params.get('name', 'db'), engine=params.get('engine', 'sql'))


def rds_engine(item, stage):
    """"Returns the engine to be used in RDS instances"""
    params = item.get('provision_params')

    if stage == 'production' and params.get('engine'):
        return PRODUCTION_RDS_ENGINES[params.get('engine')]

    return params.get('engine')


def rds_engine_params(item, stage):
    """Returns the engine to be used in database params for RDS"""
    params = item.get('provision_params')

    return '{engine}{version}'.format(
        engine=rds_engine(item, stage),
        version=params.get('version'))


def rds_param_group_name(item, stage):
    """Returns the parameter group name to use"""
    params = item.get('provision_params')
    version = str(params.get('version', 'default'))

    return 'stackmate-{engine}-{version}'.format(
        engine=rds_engine(item, stage),
        version=re.sub(r'\.', '', version))

def rds_param_group_family(item, stage):
    """Get the RDS param group family to base the parm group on"""
    params = item.get('provision_params')
    engine = rds_engine(item, stage)
    version = str(params.get('version', 'default'))

    return RDS_PARAM_GROUPS[engine][version]


def filter_mysql_items(provisions, modifications): # pylint: disable=unused-argument
    """Filters provisions & modifications for MySQL"""
    return []


def filter_postgres_items(provisions, modifications): # pylint: disable=unused-argument
    """Filters provisions & modifications for PostgreSQL"""
    return []


def get_mysql_db_usernames(mysql_info: dict) -> set:
    """
    Extracts mysql database user names from the reslt of mysql_info module
    https://docs.ansible.com/ansible/latest/modules/mysql_info_module.html
    """
    users = set()

    if not mysql_info.get('users'):
        return users

    # the 'users' entry is a dict formed [{ host: { 'user': [permissions] } }]
    for hostsdict in mysql_info['users'].values():
        for userdict in hostsdict.values():
            users.update(set(userdict.keys()))

    return users


def get_mysql_databases(mysql_info: dict) -> set:
    """
    Extracts mysql database names from the reslt of mysql_info module
    https://docs.ansible.com/ansible/latest/modules/mysql_info_module.html
    """
    return set(mysql_info.get('databases', {}).keys())


def get_stackmate_aws_databases_state(variables):
    """
    Returns the state to be used in Stackmate
    """
    resources = []
    rolename = 'databases'
    provisionables = variables['provision_items']

    for res in variables.get('rds_instances', []):
        item = None

        for prov in provisionables:
            if prov['provision_params']['name'] == res['db_instance_identifier']:
                item = prov
                break

        if item is None:
            continue

        params = item['provision_params']
        resources.append({
            'id': item['id'],
            'created_at': str(datetime.now()),
            'group': item['group'],
            'provision_params': params,
            'result': res,
            'output': {
                'resource_id': res['db_instance_identifier'],
                'ip': None,
                'nodes': [],
                'host': res['endpoint']['address'],
                'port': res['endpoint']['port'],
                'username': params.get('credentials', {}).get('username'),
                'password': params.get('credentials', {}).get('password'),
                'root_username': params.get('root_credentials', {}).get('username'),
                'root_password': params.get('root_credentials', {}).get('password'),
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
            'rds_cluster_name': rds_cluster_name,
            'rds_engine': rds_engine,
            'rds_engine_params': rds_engine_params,
            'rds_param_group_name': rds_param_group_name,
            'rds_param_group_family': rds_param_group_family,
            'rds_extract_instances': rds_extract_instances,
            'get_installables': get_installables,
            'get_mysql_databases': get_mysql_databases,
            'get_mysql_db_usernames': get_mysql_db_usernames,
            'get_stackmate_aws_databases_state': get_stackmate_aws_databases_state,
        }
