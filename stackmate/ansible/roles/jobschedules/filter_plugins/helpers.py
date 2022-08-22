"""Filters for roles that create rds instances"""
# -*- coding: utf-8 -*-
from datetime import datetime

def parse_cron_frequency(freq):
    """Parses the standard crontab frequency to components used by ansible"""
    if not freq:
        raise Exception('Frequency not specified')

    minute, hour, monthday, month, weekday = freq.split(' ')

    return {
        'minute': minute,
        'hour': hour,
        'day': monthday,
        'month': month,
        'weekday': weekday,
    }


def get_stackmate_jobschedules_state(variables):
    """Returns the stackmate state"""
    resources = []
    rolename = 'jobschedules'
    provisionables = variables['provision_items']

    for command in variables['provision_results']:
        item = None

        for prov in provisionables:
            if command == prov['provision_params']['command']:
                item = prov
                break

        if item is None:
            continue

        resources.append({
            'id': item['id'],
            'created_at': str(datetime.now()),
            'group': item['group'],
            'provision_params': item['provision_params'],
            'result': None,
            'output': {}
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
            'parse_cron_frequency': parse_cron_frequency,
            'get_stackmate_jobschedules_state': get_stackmate_jobschedules_state,
        }
