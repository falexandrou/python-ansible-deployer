"""Helper functions"""
# -*- coding: utf-8 -*-
import string
from datetime import datetime

# devices a - d are usually occupied
CHAR_RANGE = string.ascii_lowercase[5:]


def get_available_devices(ec2_instances):
    """Returns the available device names per instance"""
    mapping = {}

    device_names = ['/dev/sd' + c for c in CHAR_RANGE]
    device_names += ['/dev/xvd' + c for c in CHAR_RANGE]

    for instance in ec2_instances:
        mappings = instance.get('block_device_mappings', [])
        unavailable = list(dev['device_name'] for dev in mappings)

        available = []
        for dev in device_names:
            if not any(dev in unav for unav in unavailable):
                available.append(dev)

        instance_id = instance['instance_id']
        mapping[instance_id] = available

    return mapping


def get_volume_by_name(item, existing_volumes):
    """Returns the volume by name"""
    if item.get('provision_params', {}).get('name'):
        name = item['provision_params']['name']

        for vol in existing_volumes:
            if name == vol.get('tags', {}).get('Name'):
                return vol

    return None


def get_volume_id(item, existing_volumes):
    """Returns the volume id (if available)"""

    # volume id is present in the provision item, return it
    if item.get('id'):
        return item['id']

    vol = get_volume_by_name(item, existing_volumes)

    return vol['id'] if vol is not None else None


def get_device_name(item, existing_volumes):
    """Returns the device name (if available)"""
    existing_vol = get_volume_by_name(item, existing_volumes)

    if existing_vol:
        return existing_vol['attachment_set']['device']

    return None


def get_stackmate_aws_helpers_state(variables):
    """
    Returns the state to be used in Stackmate
    """
    resources = []
    rolename = 'volumes'
    provisionables = variables['provisions'] + variables['modifications']

    for res in variables['provisioned_volumes']:
        item = None

        for prov in provisionables:
            if prov['provision_params']['name'] == res['creation_token']:
                item = prov
                break

        if item is None:
            continue

        params = item['provision_params']
        resources.append({
            'id': ('service-%s-%s' % (rolename, params['name'])),
            'created_at': str(datetime.now()),
            'group': None,
            'provision_params': item['provision_params'],
            'result': res,
            'output': {
                'resource_id': res['file_system_id'],
                'ip': None,
                'host': res['filesystem_address'],
                'port': None,
                'nodes': [],
            }
        })

    return dict(
        role=rolename,
        resources=resources)


class FilterModule:
    """Filters used in the volumes role"""
    # pylint: disable=too-few-public-methods,no-self-use
    def filters(self):
        """Filters to be used in the role"""
        return {
            'get_available_devices': get_available_devices,
            'get_volume_id': get_volume_id,
            'get_device_name': get_device_name,
            'get_stackmate_aws_helpers_state': get_stackmate_aws_helpers_state,
        }
