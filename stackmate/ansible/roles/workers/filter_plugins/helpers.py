"""Helper functions"""
# -*- coding: utf-8 -*-
from datetime import datetime


def get_stackmate_workers_state(variables):
    """Returns the stackmate state"""
    resources = []
    rolename = 'workers'

    for item in variables['worker_items']:
        resources.append({
            'id': item['id'],
            'created_at': str(datetime.now()),
            'group': item.get('group'),
            'provision_params': item['provision_params'],
            'result': None,
            'output': None,
        })

    return dict(
        role=rolename,
        resources=resources)


class FilterModule:
    """Filters used in the instances role"""
    # pylint: disable=too-few-public-methods,no-self-use
    def filters(self):
        """Filters to be used in the role"""
        return {
            'get_stackmate_workers_state': get_stackmate_workers_state,
        }
