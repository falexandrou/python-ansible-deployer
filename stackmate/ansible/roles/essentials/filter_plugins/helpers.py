"""Helper functions"""
# -*- coding: utf-8 -*-
from datetime import datetime

def get_stackmate_essentials_state(_variables):
    """Returns the stackmate state"""

    return dict(
        role='essentials',
        resources=[{
            'id': 'utility-essentials',
            'created_at': str(datetime.now()),
            'group': 'provisionables',
            'provision_params': {},
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
            'get_stackmate_essentials_state': get_stackmate_essentials_state,
        }
