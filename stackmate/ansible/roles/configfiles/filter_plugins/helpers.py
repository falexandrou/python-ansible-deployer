"""Helper functions"""
# -*- coding: utf-8 -*-
import os
from datetime import datetime


def get_items_with_absolute_paths(items, application_dir=None, source=None):
    """Returns the destination for a file in the remote server"""
    for item in items:
        if source:
            item['provision_params'].update({
                'source': os.path.join(source, item['provision_params']['source']),
            })

        if item['provision_params'].get('application') and application_dir:
            item['provision_params'].update({
                'target': os.path.join(application_dir, item['provision_params']['target']),
            })

    return items


def get_stackmate_configfiles_state(variables):
    """Returns the state for the module"""
    resources = []
    rolename = 'configfiles'

    # re-create the provisionables as the ones in the fact, has its file path altered
    provisionables = variables.get('provisions', []) + variables.get('modifications', [])
    for item in provisionables:
        res = next(
            (f for f in variables['provisioned_files'] if f['cfg']['id'] == item['id']), None)

        resources.append(dict(
            id=item['id'],
            created_at=str(datetime.now()),
            group=item['group'], # get the config file from the loop item
            provision_params=item['provision_params'],
            result=res,
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
            'get_stackmate_configfiles_state': get_stackmate_configfiles_state,
            'get_items_with_absolute_paths': get_items_with_absolute_paths,
        }
