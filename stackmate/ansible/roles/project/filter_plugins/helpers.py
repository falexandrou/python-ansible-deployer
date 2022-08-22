"""Helper functions"""
# -*- coding: utf-8 -*-
import os
import time
from datetime import datetime

DATE_FORMAT = '%Y%m%d%H%M%S'


def process_app_env(env_str) -> dict:
    """Proceses the application environment variables into a dict"""
    environment = {}
    for export in env_str.split(' '):
        line = export.strip()

        if line.startswith('#') or '=' not in line:
            continue

        parts = line.split('=')

        if len(parts) != 2:
            continue

        varname, varvalue = parts
        environment[varname.upper()] = varvalue
    return environment


def get_services_per_group(servicelist, daemons):
    """
    Gets the services for the group
    The input would be something like:
    {'application': ['puma'], 'workers': ['sidekiq']}

    and should return something like:
    [
        {'name': 'puma', 'group': 'application'},
        {'name': 'sidekiq', 'group': 'workers'},
    ]
    """
    groupservices = []
    for srv in servicelist:
        for group, services in daemons.items():
            if srv in services:
                groupservices.append({'name': srv, 'group': group})

    return groupservices


def as_cli_option(optionvalues, optionname, separator='='):
    """Joins a list of option variables to a string of command options"""
    form = lambda opt: '{}{}{}'.format(optionname, separator, opt)
    opts = [form(opt) for opt in optionvalues]
    return ' '.join(list(opts))


def splitstring(string, separator):
    """Splits a string based on a separator"""
    return string.strip().split(separator)


def get_sorted_release_dirs(paths):
    """Returns the release directories as a sorted set"""
    mapping = {}
    for path in paths:
        timestamp = time.mktime(
            time.strptime(os.path.basename(path), DATE_FORMAT))
        mapping[timestamp] = path

    return list([path for dt, path in sorted(mapping.items(), reverse=True)])


def get_rollback_target_release(paths):
    """Gets the release that we should roll back to"""
    if len(paths) <= 1:
        return None

    sortedpaths = get_sorted_release_dirs(paths)
    return sortedpaths[1:2][0]


def get_obsolete_releases(paths, keep=5):
    """Returns the paths to clean up so that we can only keep 5 releases"""
    if len(paths) <= keep:
        return []

    sortedpaths = get_sorted_release_dirs(paths)
    return sortedpaths[keep:]


def get_stackmate_project_state(variables):
    """
    Returns the stackmate state

    Found in provision params:
        - framework
        - scm
        - provider
        - github_deploy_key_name
        - repository: "git@github.com:stackmate-io/sample-app-django3.git"
        - branch
        - deployment_path
        - region: eu-central-1
        - daemons
        - statics
        - appconfigs
        - pipeline

    Generated information:
        - release path
        - whether the deployment was successful
        - removed releases
    """
    keys = [
        # provision params
        'framework', 'scm', 'provider', 'github_deploy_key_name',
        'repository', 'branch', 'deployment_path', 'region',
        'daemons', 'statics', 'appconfigs', 'pipeline',
        # generated facts
        'release_path',
        'release_success',
        'removed_releases',
    ]

    return dict(
        role='project',
        resources=[{
            'id': 'utility-project',
            'created_at': str(datetime.now()),
            'group': None,
            'provision_params': {key: variables.get(key) for key in keys},
            'result': None,
            'output': None,
        }]
    )


class FilterModule:
    """Filters used in the instances role"""
    # pylint: disable=too-few-public-methods,no-self-use
    def filters(self):
        """Filters to be used in the role"""
        return {
            'splitstring': splitstring,
            'process_app_env': process_app_env,
            'as_cli_option': as_cli_option,
            'get_obsolete_releases': get_obsolete_releases,
            'get_services_per_group': get_services_per_group,
            'get_rollback_target_release': get_rollback_target_release,
            'get_stackmate_project_state': get_stackmate_project_state,
        }
