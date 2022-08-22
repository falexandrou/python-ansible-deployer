# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915,E0401,E0611
import json
import types
from stackmate.deployables.utility import Utility
from stackmate.ansible.roles.project.filter_plugins.helpers \
    import FilterModule, get_stackmate_project_state

OUTPUT_FILE = 'stackmate/ansible/roles/project/' \
            + 'molecule/instances-rollback/' \
            + 'provisioning-output.json'

PROVISION_VARS = None
with open(OUTPUT_FILE) as output:
    PROVISION_VARS = json.load(output)


def test_filter_exported():
    filters = FilterModule().filters()
    assert 'get_stackmate_project_state' in filters
    assert isinstance(filters['get_stackmate_project_state'], types.FunctionType)


def test_get_stackmate_project_state():
    state = get_stackmate_project_state(PROVISION_VARS)
    util = Utility.factory(kind='project')
    assert isinstance(state, dict)
    assert state['role'] == 'project'
    assert len(state['resources']) == 1
    assert isinstance(state['resources'][0], dict)
    resource = state['resources'][0]
    assert not resource['group']
    assert resource['id'] == util.deployable_id
    assert resource['created_at']

    provisions = resource['provision_params']

    assert sorted(list(provisions.keys())) == sorted([
        'framework', 'scm', 'provider', 'github_deploy_key_name',
        'repository', 'branch', 'deployment_path', 'region',
        'daemons', 'statics', 'appconfigs', 'pipeline',
        'release_path',
        'release_success',
        'removed_releases',
    ])

    assert provisions['framework'] == 'django'
    assert provisions['scm'] == 'github'
    assert provisions['github_deploy_key_name'] == 'molecule-test-key'
    assert provisions['repository'] == 'git@github.com:stackmate-io/sample-app-django3.git'
    assert provisions['branch'] == 'main'
    assert provisions['release_success']
    assert isinstance(provisions['removed_releases'], list)
