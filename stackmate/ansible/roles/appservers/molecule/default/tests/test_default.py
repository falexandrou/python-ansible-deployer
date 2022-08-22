# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915
import os
import json
import pytest
import testinfra.utils.ansible_runner

SYSTEMD_ENTRIES = ['gunicorn', 'pm2', 'puma']

ROOT_APPSERVERS = ['gunicorn', 'puma']

TESTINFRA_HOSTS = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']
).get_hosts('all')

PROVISIONING_OUTPUT = None
with open('./provisioning-output.json') as output:
    PROVISIONING_OUTPUT = json.load(output)


HEADER_DECLARATIONS = [
    'proxy_redirect off;',
    'proxy_http_version 1.1;',
    'proxy_set_header Host $host;',
    'proxy_set_header Upgrade $http_upgrade;',
    'proxy_set_header Connection "upgrade";',
    'proxy_set_header X-NginX-Proxy true;',
    'proxy_set_header X-Real-IP $remote_addr;',
    'proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;',
    'proxy_set_header X-Forwarded-Proto https',
    'add_header X-Frame-Options SAMEORIGIN;',
    'add_header X-Content-Type-Options nosniff;',
    'add_header X-XSS-Protection "1;mode=block";',
]

SERVICE_COMMANDS = [
    ('gunicorn', dict(
        start='/usr/local/bin/gunicorn myapp.wsgi -b "127.0.0.1:3000"',
        stop="/bin/kill -TSTP $MAINPID",
        reload="/bin/kill -s HUP $MAINPID")),
    ('pm2', dict(
        start="/usr/local/bin/pm2 start",
        stop="/usr/local/bin/pm2 kill",
        reload="/usr/local/bin/pm2 reload all")),
    ('puma', dict(
        start="/usr/bin/env bundle exec puma -C /var/www/application/current/",
        stop="/bin/kill -TSTP $MAINPID",
        reload="/bin/kill -s HUP $MAINPID")),
]


def test_packages_installed(host):
    packages = host.pip_package.get_packages()
    assert 'gunicorn' in packages
    assert 'daphne' not in packages

    assert host.file('/usr/local/bin/puma').exists
    assert host.file('/usr/local/bin/pm2').exists


@pytest.mark.parametrize('service', SYSTEMD_ENTRIES)
def test_systemd_files_created(host, service):
    assert host.file('/etc/systemd/system/{}.service'.format(service)).exists
    assert host.file('/etc/systemd/system/{}.target'.format(service)).exists
    assert host.file('/etc/systemd/system/{}.socket'.format(service)).exists


@pytest.mark.parametrize('commandset', SERVICE_COMMANDS)
def test_commands(host, commandset):
    service, commands = commandset

    filename = '/etc/systemd/system/{}.service'.format(service)
    file = host.file(filename)

    cmdmap = dict(start='ExecStart', stop='ExecStop', reload='ExecReload')

    for key, cmd in commands.items():
        if cmd is not None:
            lookup = '%s=%s' % (cmdmap[key], cmd)
            assert file.contains(lookup)
        else:
            assert not file.contains('{}='.format(cmdmap[key]))


"""
Sample nginx configuration file:

server {
     listen 80 default_server;

     location /elb-status {
       access_log off;
       return 200;
     }
    }

    upstream gunicorn {
       server http://127.0.0.1:3000 max_fails=3 fail_timeout=30s;
    }
    upstream daphne {
       server http://127.0.0.1:3100 max_fails=3 fail_timeout=30s;
    }
    upstream pm2 {
       server http://127.0.0.1:4000 max_fails=3 fail_timeout=30s;
    }
    upstream puma {
       server http://127.0.0.1:5000 max_fails=3 fail_timeout=30s;
    }

    server {
        # server configuration
        listen 80 default_server;
        server_name ezploy.eu www.ezploy.eu;
        try_files $uri/index.html $uri @gunicorn @puma;
        keepalive_timeout 5;

        # headers configuration
        add_header Strict-Transport-Security "max-age=63072000;\
        includeSubdomains; preload";

        # document root - managed by Stackmate
        root /var/www/application/current;

        # log paths - managed by Stackmate
        access_log /var/log/nginx/ezploy.eu.access.log compression;
        error_log /var/log/nginx/ezploy.eu.error.log compression;

       proxy_http_version 1.1;
       proxy_set_header Upgrade $http_upgrade;
       proxy_set_header Connection "upgrade";

       proxy_redirect off;

       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       proxy_set_header X-Forwarded-Host $server_name;
       proxy_set_header X-Forwarded-Proto $scheme;

        # cache static files as much as possible
        location ^~ \\.(ico|css|gif|jpe?g|png|js)(?[0-9]+)\\?$ {
           gzip_static on;
           expires max;
           break;
        }


        location ^~ /static {
           root /var/www/application/current/static;
           add_header Cache-Control public;
           gzip_static on;
           expires max;
        }

        # gunicorn server configuration - Managed by Stackmate
        location @gunicorn {
           proxy_pass http://gunicorn;
        }

        # daphne server configuration - Managed by Stackmate
        location /channels {
           proxy_pass http://daphne;
        }

        # pm2 server configuration - Managed by Stackmate
        location /node-application {
           proxy_pass http://pm2;
       }

        # puma server configuration - Managed by Stackmate
        location @puma {
           proxy_pass http://puma;
        }
    }
"""


def test_nginx_configuration(host):
    cfg = host.file('/etc/nginx/sites-available/ezploy.eu.conf')
    assert cfg.exists
    assert cfg.is_file
    assert 'server_name ezploy.eu www.ezploy.eu;' in cfg.content_string


@pytest.mark.parametrize('server', ROOT_APPSERVERS)
def test_upstream_locations_in_nginx_root(host, server):
    cfg = host.file('/etc/nginx/sites-available/ezploy.eu.conf')
    assert 'upstream {}'.format(server) in cfg.content_string
    assert 'location @{}'.format(server) in cfg.content_string
    assert 'proxy_pass http://{}'.format(server) in cfg.content_string


def test_upstream_locations_in_nginx_uri(host):
    cfg = host.file('/etc/nginx/sites-available/ezploy.eu.conf')

    # pm2 upstream should be without an @ symbol
    assert 'upstream pm2' in cfg.content_string
    assert 'location /node-application' in cfg.content_string
    assert 'proxy_pass http://pm2' in cfg.content_string

    # daphne should not be part of the configuration, as it's terminated
    assert 'upstream daphne' not in cfg.content_string
    assert 'location /channels' not in cfg.content_string
    assert 'proxy_pass http://daphne' not in cfg.content_string


@pytest.mark.parametrize('declaration', HEADER_DECLARATIONS)
def test_nginx_header_declarations(host, declaration):
    cfg = host.file('/etc/nginx/sites-available/ezploy.eu.conf')
    assert declaration in cfg.content_string


def test_stackmate_state_generated():
    assert 'stackmate_state' in PROVISIONING_OUTPUT
    assert isinstance(PROVISIONING_OUTPUT['stackmate_state'], list)
