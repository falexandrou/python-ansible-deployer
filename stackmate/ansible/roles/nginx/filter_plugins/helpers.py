"""Helper functions"""
# -*- coding: utf-8 -*-
from datetime import datetime


def get_stackmate_nginx_state(variables):
    """Returns the stackmate state"""
    rolename = 'nginx'
    resources = []

    for item in variables['provision_items']:
        resources.append({
            'id': item['id'],
            'group': item['group'],
            'created_at': str(datetime.now()),
            'provision_params': item['provision_params'],
            'result': None,
            'output': None,
        })

    return dict(role=rolename, resources=resources)


class FilterModule:
    """Filters used in the instances role"""
    # pylint: disable=too-few-public-methods,no-self-use
    def filters(self):
        """Filters to be used in the role"""
        return {
            'get_stackmate_nginx_state': get_stackmate_nginx_state,
        }
