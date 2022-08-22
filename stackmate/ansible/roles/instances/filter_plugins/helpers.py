"""Filters for roles that create ec2_instances"""
# -*- coding: utf-8 -*-
import json
import hashlib
from datetime import datetime

def extract_instances(results):
    """
    Extract the instance dictionaries from an ec2_instance result
    """
    instances = []

    for entry in results:
        if entry.get('instances'):
            for instance in entry['instances']:
                instances.append(instance)

    return instances


def extract_instance_ids(results):
    """
    Extracts the instance ids from an ec2_instance result
    The point is that when the instance exists, the module returns:
    - { instance_ids: [....] }
    while on the other hand, it returns a full module's result
    """
    instance_ids = []

    for entry in results:
        if entry.get('instances'):
            for instance in entry['instances']:
                instance_ids.append(instance['instance_id'])
        elif entry.get('instance_ids'):
            for instance_id in entry['instance_ids']:
                instance_ids.append(instance_id)

    return instance_ids


def get_stackmate_aws_instances_state(variables):
    """
    Returns the state to be used in Stackmate
    """
    rolename = 'instances'
    instances = variables['provision_results']
    entries = {}

    for item in variables['provision_items']:
        # entry is missing from the entries collection, add it
        itemid = item['id']
        name = item['provision_params']['name']

        if itemid not in entries:
            entries[itemid] = {
                'id': item['id'],
                'created_at': str(datetime.now()),
                'group': item['group'],
                'result': instances,
                'provision_params': item['provision_params'],
                'output': {
                    'resource_id': None,
                    'ip': None,
                    'host': None,
                    'port': None,
                    'nodes': [],
                },
            }

        # find all entries related to this provision item
        instance_result = next(
            (res for res in instances if res['tags']['ServiceName'] == name),
            None
        )

        if not instance_result:
            continue

        entries[itemid]['output']['nodes'].append({
            'name': name,
            'resource_id': instance_result['instance_id'],
            'ip': instance_result.get('public_ip_address'),
            'host': instance_result.get('public_dns_name'),
            'port': None,
        })

    return dict(
        role=rolename,
        resources=list(entries.values()))


def get_idempotency_token(item, length=10):
    """Returns the idempotency token based on the item's provision params"""
    params_str = json.dumps(item['provision_params'])
    return hashlib.md5(params_str.encode('utf-8')).hexdigest()[:length]


def get_idempotent_instance_name(item):
    """Returns an idempotent name for the deployable"""
    return '{name}-{hash}'.format(
        name=item['provision_params']['name'],
        hash=get_idempotency_token(item))


def get_availability_zone(item):
    """Returns the availability zone to use in the instance creation"""
    hashlength = len(get_idempotency_token(item))
    region = item['provision_params'].get('region', 'eu-central-1')
    zone = 'a'

    if hashlength % 3 == 0:
        zone = 'b'
    elif hashlength % 5 == 0:
        zone = 'c'

    return '{region}{zone}'.format(region=region, zone=zone)


class FilterModule:
    """Filters used in the instances role"""
    # pylint: disable=too-few-public-methods

    def filters(self):
        """Filters to be used in the role"""
        # pylint: disable=no-self-use
        return {
            'extract_instances': extract_instances,
            'extract_instance_ids': extract_instance_ids,
            'get_stackmate_aws_instances_state': get_stackmate_aws_instances_state,
            'get_idempotency_token': get_idempotency_token,
            'get_availability_zone': get_availability_zone,
            'get_idempotent_instance_name': get_idempotent_instance_name,
        }
