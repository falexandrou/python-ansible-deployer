"""Helper functions"""
# -*- coding: utf-8 -*-
import re
from datetime import datetime


def github_repository_parts(repository, key=None):
    """Breaks the repository into parts"""
    owner, name = re.match(r'^git@github\.com:([^\/]+)\/([^\.]+)\.git', repository).groups()
    parts = {'owner': owner, 'name': name}
    return parts.get(key) if key else parts

def get_stackmate_aws_prepare_state(variables):
    """Returns the state to be used in Stackmate"""
    rolename = 'prepare'
    resources = []

    keyresult = None
    if variables['scm'] == 'github':
        keyresult = variables.get('github_deploy_key', {}).get('key')

    output = {
        'deploy_key_id': keyresult.get('id') if isinstance(keyresult, dict) else None,
        'public_key': keyresult.get('key') if isinstance(keyresult, dict) else None,
    }

    if variables['provider'] == 'aws':
        output.update({'cloud_user_id': variables['aws_user_info']['arn']})

    resources.append({
        'id': 'utility-prepare',
        'created_at': str(datetime.now()),
        'group': None,
        'provision_params': {
            'scm': variables['scm'],
            'repository': variables['repository'],
        },
        'result': None,
        'output': output,
    })

    return dict(
        role=rolename,
        resources=resources
    )


class FilterModule:
    """Filters used in the instances role"""
    # pylint: disable=too-few-public-methods

    def filters(self):
        """Filters to be used in the role"""
        # pylint: disable=no-self-use
        return {
            'github_repository_parts': github_repository_parts,
            'get_stackmate_aws_prepare_state': get_stackmate_aws_prepare_state,
        }
