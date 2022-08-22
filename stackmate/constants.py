"""Constants"""
# -*- coding: utf-8 -*-
import os

VERSION = '1.0.0'
LOCALHOST = 'localhost'
PREVIEW_DOMAIN = 'myappis.live'
PREVIEW_DOMAIN_HOSTED_ZONE_ID = 'Z0564469EQGYD5L6BOXJ'

PROVIDER_AWS = 'aws'

# Play related constants
CONNECTION_LOCAL = 'local'
CONNECTION_SSH = 'ssh'

STRATEGY_LINEAR = 'linear'
STRATEGY_PARALLEL = 'free'
STRATEGY_MITOGEN_LINEAR = 'mitogen_linear'
STRATEGY_MITOGEN_PARALLEL = 'mitogen_free'

DEPLOYMENT_USER = 'stackmate'

# facts used in the ansible roles
STACKMATE_STATE_FACT = 'stackmate_state'
STACKMATE_ACTION_FACT = 'stackmate_user_action'
STACKMATE_CREDENTIALS = 'stackmate_generated_credentials'

# Deployment status
DEPLOYMENT_STARTED = 'started'
DEPLOYMENT_SUCCESS = 'success'
DEPLOYMENT_FAILURE = 'failure'
DEPLOYMENT_CANCEL = 'cancelled'

# Project types
PROJECT_TYPE_RAILS = 'rails'
PROJECT_TYPE_SINATRA = 'sinatra'
PROJECT_TYPE_DJANGO = 'django'
PROJECT_TYPE_FLASK = 'flask'
PROJECT_TYPE_STATIC = 'static'
PROJECT_TYPE_NODEJS = 'nodejs'

LOCAL_DEPLOYMENT_PROJECT_TYPES = [
    PROJECT_TYPE_STATIC,
]

PROJECT_TYPES = [
    PROJECT_TYPE_RAILS,
    PROJECT_TYPE_SINATRA,
    PROJECT_TYPE_DJANGO,
    PROJECT_TYPE_FLASK,
    PROJECT_TYPE_STATIC,
    PROJECT_TYPE_NODEJS,
]

# Project deployment flavors
PROJECT_FLAVOR_INSTANCES = 'instances'
PROJECT_FLAVOR_STATIC = 'static'
PROJECT_FLAVOR_KUBERNETES = 'kubernetes'
PROJECT_FLAVOR_DEDICATED = 'dedicated'
PROJECT_FLAVORS = [
    PROJECT_FLAVOR_INSTANCES,
    PROJECT_FLAVOR_STATIC,
    PROJECT_FLAVOR_KUBERNETES,
    PROJECT_FLAVOR_DEDICATED,
]

# Environment variable names available
ENV_CHECK_MODE = 'STACKMATE_DRY_RUN'
ENV_PUBLIC_KEY = 'STACKMATE_PUBLIC_KEY'
ENV_PRIVATE_KEY = 'STACKMATE_PRIVATE_KEY'
ENV_MITOGEN_PATH = 'STACKMATE_MITOGEN_PATH'
ENV_STACKMATE_OPERATION_ID = 'STACKMATE_OPERATION_ID'

# Services that are loadbalanced
LOAD_BALANCED_SERVICES = {'application'}

# Deployer task actions
TASK_ACTION_START = 'start'
TASK_ACTION_SUCCESS = 'success'
TASK_ACTION_FAILURE = 'failure'
TASK_ACTION_SKIP = 'skip'

# Deployer output type
OUTPUT_TYPE_DEPLOYMENT = 'deployment'
OUTPUT_TYPE_GROUP = 'group'
OUTPUT_TYPE_TASK = 'task'

# Env variables
CHECK_MODE = os.environ.get(ENV_CHECK_MODE, False)
OPERATION_ID = os.environ.get(ENV_STACKMATE_OPERATION_ID)
MITOGEN_PATH = os.environ.get(ENV_MITOGEN_PATH, None)

# Playbook related constants
OMNIPRESENT_ROLES = dict([
    (PROJECT_FLAVOR_INSTANCES, set(['prepare', 'project', 'notifications'])),
    (PROJECT_FLAVOR_STATIC, set()),
    (PROJECT_FLAVOR_KUBERNETES, set()),
    (PROJECT_FLAVOR_DEDICATED, set()),
])

FLATTENED_PROVISION_PARAM_ROLES = set([
    'project', 'prepare', 'essentials', 'notifications', 'prerequisites',
])

INVENTORY_INCLUDED_ROLES = ['instances']

# Keys to preserve from the original resource output,
# when they're specified as empty in a state update process
STATE_OUTPUT_PRESERVED_KEYS = [
    'username', 'password', 'root_username', 'root_password',
    'key_id', 'secret', 'host',
    'smtp_username', 'smtp_password', 'smtp_host',
]

BECOME_METHOD_SUDO = 'sudo'

FORCED_STRATEGIES_PER_ROLE = {
    # force the mailer to use the plain linear strategy, due to a segfault in mitogen
    'mailer': STRATEGY_LINEAR,
}

# Increase the number of ansible forks
ANSIBLE_FORKS_NUM = 100


# Attributes that can be found in the configuration file with a different name
CONFIG_RENAMED_ATTRIBUTES = {
    'type': 'kind',
}

# Maps the deployable kinds to ansible roles
DEPLOYABLE_KIND_TO_ROLE_MAPPING = {
    # Services
    'application': 'instances',
    'worker': 'instances',
    'backend': 'instances',
    'cdn': 'cdn',
    'elasticstorage': 'elasticstorage',

    # Dependencies or Standalone Services
    'mysql': 'databases',
    'nginx': 'nginx',
    'php': 'php',
    'redis': 'caches',
    'memcached': 'caches',
    'ruby': 'ruby',
    'postgresql': 'databases',
    'mailer': 'mailer',
    'nodejs': 'nodejs',
    'sidekiq': 'workers',
    'resque': 'workers',
    'celery': 'workers',
    'runworker': 'workers',
    'daphne': 'appservers',
    'puma': 'appservers',
    'gunicorn': 'appservers',
    'pm2': 'appservers',
    'python': 'python',

    # Utilities
    'essentials': 'essentials',
    'configfiles': 'configfiles',
    'environment': 'environment',
    'jobschedules': 'jobschedules',
    'volumes': 'volumes',
    'ssl': 'ssl',
    'prerequisites': 'prerequisites',
    'prepare': 'prepare',
    'project': 'project',
    'routing': 'routing',

    # internals
    'notifications': 'notifications',
    'systemd': 'systemd',
}

# Specifies which role depends on which
ROLE_TO_DEPENDS_ON_MAPPING = {
    'prepare': [],
    'prerequisites': [],
    'ssl': ['prerequisites'],
    'instances': ['prerequisites'],
    'essentials': ['instances'],
    'databases': ['prerequisites', 'instances'],
    'elasticstorage': ['prerequisites', 'instances'],
    'volumes': ['prerequisites', 'instances'],
    'caches': ['prerequisites', 'instances'],
    'mailer': ['prerequisites', 'instances'],
    'cdn': ['ssl', 'prerequisites'],
    'nginx': ['instances'],
    'nodejs': ['instances'],
    'python': ['instances'],
    'ruby': ['instances'],
    'configfiles': ['instances'],
    'project': ['instances'],
    'environment': ['instances', 'ruby', 'nodejs', 'python'],
    'appservers': ['instances', 'ruby', 'nodejs', 'python'],
    'workers': ['instances', 'ruby', 'nodejs', 'python'],
    'jobschedules': ['instances'],
    'routing': ['ssl', 'instances'],
    'notifications': [],
    'systemd': [],
}

# The deployables that can have a `nodes` attributes which makes them
# expand into multiple Deployable instances
DEPLOYABLE_KINDS_WITH_EXPANDABLE_NODES = [
    'application',
    'backend',
    'workers',
]

# the keys to check for credentials in the state
STATE_CREDENTIAL_KEYS = {
    'mailer': [
        'root_username', 'root_password', 'username', 'password', 'smtp_username', 'smtp_password',
    ],
    'elasticstorage': [
        'username', 'password', 'root_username', 'root_password',
    ],
}

# Keys that should be ignored during the diffing of two similar deployables
DIFF_IGNORE_KEYS = ['name', 'nodes']

# Use this tag to ignore a task's output
LIVE_OUTPUT_TAG = 'live_output'
COMMAND_VAR_TAG = 'has_command_var'
IGNORE_EMPTY_OUTPUT_TAG = 'ignore_empty_output'

# How many attempts should we do in order to get an APT lock
APT_RETRIES = 50
APT_DELAY = 15
