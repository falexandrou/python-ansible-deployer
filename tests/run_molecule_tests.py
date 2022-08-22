import os
import re
import subprocess
import copy
import boto3

def split_env_var(varname):
    """Splits a comma separated environment variable"""
    return list([r.strip() for r in os.environ.get(varname, '').split(',') if r])

LINT_ONLY = int(os.environ.get('LINT_ONLY', '0'))
ASSUME_ROLE = int(os.environ.get('ASSUME_ROLE', '1'))
SPECIFIC_SCENARIOS = split_env_var('SPECIFIC_SCENARIOS')
SPECIFIC_ROLES = split_env_var('SPECIFIC_ROLES')
STACKMATE_ACCESS_KEY = os.environ.get('STACKMATE_PROVISIONER_ACCESS_KEY_ID')
STACKMATE_SECRET = os.environ.get('STACKMATE_PROVISIONER_SECRET_ACCESS_KEY')
STACKMATE_ROLE_ARN = os.environ.get('STACKMATE_ROLE_ARN')
STACKMATE_ROLE_EXTERNAL_ID = os.environ.get('STACKMATE_ROLE_EXTERNAL_ID')
SESSION_DURATION = os.environ.get('STACKMATE_SESSION_DURATION', 3600 * 12)
ROLES_DIR = os.path.join('stackmate', 'ansible', 'roles')
MOLECULE_TESTS = {}


if ASSUME_ROLE:
    if not STACKMATE_ACCESS_KEY or not STACKMATE_SECRET:
        raise ValueError(
            'Please specify the STACKMATE_PROVISIONER_ACCESS_KEY_ID and STACKMATE_PROVISIONER_SECRET_ACCESS_KEY variables')

    if not STACKMATE_ROLE_ARN or not STACKMATE_ROLE_EXTERNAL_ID:
        raise ValueError(
            'Please specify the STACKMATE_ROLE_ARN and STACKMATE_ROLE_EXTERNAL_ID variables')

    STS_CLIENT = boto3.client('sts',
                              aws_access_key_id=STACKMATE_ACCESS_KEY,
                              aws_secret_access_key=STACKMATE_SECRET)

    RESPONSE = STS_CLIENT.assume_role(
        RoleArn=STACKMATE_ROLE_ARN,
        ExternalId=STACKMATE_ROLE_EXTERNAL_ID,
        RoleSessionName='StackmateDeploymentTests',
        DurationSeconds=SESSION_DURATION)

    if not RESPONSE.get('Credentials'):
        raise ValueError('Something went wrong while requesting the STS credentials')

    ACCESS_KEY_ID = RESPONSE['Credentials']['AccessKeyId']
    SECRET_ACCESS_KEY = RESPONSE['Credentials']['SecretAccessKey']
    SESSION_TOKEN = RESPONSE['Credentials']['SessionToken']

    # Reset the environment variables
    os.environ.update({
        'STACKMATE_ACCESS_KEY': ACCESS_KEY_ID,
        'STACKMATE_SECRET': SECRET_ACCESS_KEY,
        'STACKMATE_STS_TOKEN': SESSION_TOKEN,
        'STACKMATE_ROOT_ACCESS_KEY': STACKMATE_ACCESS_KEY,
        'STACKMATE_ROOT_SECRET': STACKMATE_SECRET,
    })


for root, subdirs, files in os.walk(ROLES_DIR):
    if not root.endswith('molecule'):
        continue

    MOLECULE_TESTS[root] = subdirs

ENV_COPY = copy.deepcopy(os.environ)

SCENARIOS = []

for moleculedir, scenarios in MOLECULE_TESTS.items():
    execdir = re.sub(r'^(.*)\/molecule$', '\\1', moleculedir)
    rolename = re.sub(ROLES_DIR, '', execdir).strip('/')

    if SPECIFIC_ROLES and rolename not in SPECIFIC_ROLES:
        continue

    runnable_scenarios = SPECIFIC_SCENARIOS if SPECIFIC_SCENARIOS else scenarios

    for scenario in runnable_scenarios:
        SCENARIOS.append(
            (scenario, execdir),
        )

# Lint the tests first so that we don't waste too much time for lint errors
for scenario, execdir in SCENARIOS:
    subprocess.run(
        ['molecule', 'lint', '-s', scenario], cwd=execdir, check=True, env=ENV_COPY)

# Now go through the tests
for scenario, execdir in SCENARIOS:
    subprocess.run(
        ['molecule', 'test', '-s', scenario], cwd=execdir, check=True, env=ENV_COPY)
