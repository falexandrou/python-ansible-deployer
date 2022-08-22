"""Helper functions"""
# -*- coding: utf-8 -*-
from datetime import datetime


def get_stackmate_envs_state(variables):
    """Returns the state for the module"""
    rolename = 'environment'
    resources = []

    provisionables = variables.get('provisions', []) + variables.get('modifications', [])

    for item in provisionables:
        resources.append(dict(
            id=item['id'],
            created_at=str(datetime.now()),
            group=item['group'], # get the config file from the loop item
            provision_params=item['provision_params'],
        ))

    return dict(
        role=rolename,
        resources=resources)


class FilterModule:
    """Filters used in the instances role"""
    # pylint: disable=too-few-public-methods,no-self-use
    def filters(self):
        """Filters to be used in the role"""
        return {
            'get_stackmate_envs_state': get_stackmate_envs_state,
        }
