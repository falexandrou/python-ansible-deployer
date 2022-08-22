"""Helper functions"""
# -*- coding: utf-8 -*-
import re
from datetime import datetime

def upstream_name(itemname):
    """Returns the name of the upstream for use in the nginx configuration"""
    return re.sub(r'([^\w0-9\-])+', '_', itemname)


def socket_path(itemname):
    """Returns the path to the unix socket for the server"""
    return 'unix:///tmp/{}.sock'.format(upstream_name(itemname))


def is_top_level(domain):
    """Returns whether a domain is top-level"""
    return domain and len(domain.split('.')) == 2


def server_redirects(domain):
    """Returns the redirects for a domain"""
    return [domain] if is_top_level(domain) else []


def primary_domain_name(domain):
    """Returns the primary domain name"""
    return 'www.{}'.format(domain) if is_top_level(domain) else domain


def nginx_domain_names(domain):
    """Returns the domain names to be used with servername"""
    return set([domain, primary_domain_name(domain)])


def upstream_endpoint(item, default_port=3000):
    """Returns the upstream endpoint"""
    params = item.get('provision_params', {})
    return '127.0.0.1:{port}'.format(port=params.get('port', default_port))


def nginx_location_name(item):
    """Returns the nginx location name (eg. @app)"""
    params = item.get('provision_params', {})

    if not params.get('uri', '/') == '/':
        return params['uri']

    return '@{}'.format(upstream_name(params.get('name', 'app')))


def nginx_locations(items):
    """Returns the list of the nginx locations"""
    locations = []
    for item in items:
        name = nginx_location_name(item)

        if name.startswith('@'):
            locations.append(name)

    return locations


def get_stackmate_appservers_state(variables):
    """Forms the state for the role"""
    resources = []

    for item in variables['provisionables']:
        resources.append({
            'id': item['id'],
            'created_at': str(datetime.now()),
            'group': item['group'],
            'provision_params': item['provision_params'],
        })

    return dict(
        role='appservers',
        resources=resources,
    )


class FilterModule:
    """Filters used in the instances role"""
    # pylint: disable=too-few-public-methods,no-self-use
    def filters(self):
        """Filters to be used in the role"""
        return {
            'upstream_name': upstream_name,
            'socket_path': socket_path,
            'is_top_level': is_top_level,
            'server_redirects': server_redirects,
            'primary_domain_name': primary_domain_name,
            'upstream_endpoint': upstream_endpoint,
            'nginx_location_name': nginx_location_name,
            'nginx_locations': nginx_locations,
            'nginx_domain_names': nginx_domain_names,
            'get_stackmate_appservers_state': get_stackmate_appservers_state,
        }
