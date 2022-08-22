# -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915,too-many-locals
import os
import re
import copy
import pytest
from doubles import allow
from stackmate.project import Project
from stackmate.constants import LOCALHOST, CONNECTION_LOCAL, CONNECTION_SSH, \
                                STRATEGY_MITOGEN_LINEAR, STRATEGY_MITOGEN_PARALLEL, \
                                DEPLOYMENT_USER, BECOME_METHOD_SUDO

from stackmate.state import State
from stackmate.provisioner import Provisioner
from stackmate.playbooks import PlaybookIterator, Playbook, Play, OPERATIONS

def get_playbook_iterator(dirname, stage='production', operation='deployment'):
    """Returns a playbook iterator from a given directory"""
    directory = os.path.abspath(os.path.join('tests', 'data', dirname))
    assert os.path.isdir(directory)

    project = Project.load(rootpath=directory, stage=stage)
    state = State(rootpath=directory, stage=stage)
    allow(state).save.and_return(True)
    return PlaybookIterator(operation, project, state)


def get_play(project, state, role, additionals=None):
    rolename = role['name']

    deployables_list = list(filter((d for d in project.deployables if d.rolename == rolename), []))
    extra_vars = {
        'extravar1': 140,
        'operation_url': 'https://stackmate.io/operations/1',
    }

    extra_vars.update(additionals if additionals else {})
    allow(state).save.and_return(True)
    changes = Provisioner.changes(deployables_list, state.get_resources(rolename))
    return Play(role, changes, **extra_vars)


def get_plays_and_roles(iterator):
    roles = set()
    plays = []

    for playbook in iter(iterator):
        pbplays, _ignore = playbook.get_plays()
        plays += pbplays

        for play in pbplays:
            playroles = [
                t['args']['name'] for t in play.tasks if t['action'] == 'include_role'
            ]

            roles.update(playroles)

    return plays, roles


def describe_play():
    @pytest.fixture
    def instances_role():
        return {
            'name': 'instances',
            'hosts': 'localhost',
            'execution': 'linear',
        }

    @pytest.fixture
    def nginx_role():
        return {
            'name': 'nginx',
            'hosts': 'all',
            'execution': 'free',
        }

    @pytest.fixture
    def notifiers(project):
        return list(filter((d for d in project.deployables if d.rolename == 'notifications'), []))

    @pytest.fixture
    def global_vars(project):
        return project.serialize()

    @pytest.fixture
    def instances_play(project, state, instances_role, notifiers, global_vars):
        return get_play(project, state, instances_role, {
            'notifiers': notifiers,
            'global_vars': global_vars,
        })

    @pytest.fixture
    def nginx_play(project, state, nginx_role, notifiers, global_vars):
        return get_play(project, state, nginx_role, {
            'notifiers': notifiers,
            'global_vars': global_vars,
        })

    def it_initializes_correctly(instances_play, nginx_play):
        assert isinstance(instances_play, Play)
        assert isinstance(nginx_play, Play)
        assert instances_play.rolename == 'instances'
        assert nginx_play.rolename == 'nginx'

    def it_returns_the_correct_connection(instances_play, nginx_play):
        assert instances_play.connection == CONNECTION_LOCAL
        assert nginx_play.connection == CONNECTION_SSH

    def it_returns_the_correct_hosts(instances_play, nginx_play):
        assert instances_play.hosts == 'localhost'
        assert nginx_play.hosts == 'all'

    def it_returns_whether_it_is_local(instances_play, nginx_play):
        assert instances_play.is_local()
        assert not nginx_play.is_local()

    def it_returns_the_correct_strategy(instances_play, nginx_play):
        # mitogen is not enabled by default
        assert instances_play.strategy == STRATEGY_MITOGEN_LINEAR
        assert nginx_play.strategy == STRATEGY_MITOGEN_PARALLEL

        # enable mitogen explicitly
        instances_play.enable_mitogen = True
        nginx_play.enable_mitogen = True

        assert instances_play.strategy == STRATEGY_MITOGEN_LINEAR
        assert nginx_play.strategy == STRATEGY_MITOGEN_PARALLEL

    def it_returns_whether_we_should_gather_facts(instances_play, nginx_play):
        assert not instances_play.gather_facts
        assert nginx_play.gather_facts

    def it_forces_local_plays(project, state, nginx_role):
        play = get_play(project, state, nginx_role, {'force_local': True})
        assert play.is_local()

    def it_returns_the_variables(instances_play, global_vars):
        assert instances_play.get_variables() == global_vars

    def it_returns_the_correct_tasks(instances_play, nginx_play):
        instance_tasks = instances_play.tasks
        assert len(instance_tasks) == 1
        assert all(t['action'] == 'include_role' for t in instance_tasks)
        assert all(t['args'] == {'name': 'instances'} for t in instance_tasks)
        assert all(t['vars'] for t in instance_tasks)
        assert all(t['vars']['has_changes'] for t in instance_tasks)

        nginx_tasks = nginx_play.tasks
        assert len(nginx_tasks) == 1
        assert all(t['action'] == 'include_role' for t in nginx_tasks)
        assert all(t['args'] == {'name': 'nginx'} for t in nginx_tasks)
        assert all(t['vars'] for t in nginx_tasks)
        assert all(t['vars']['has_changes'] for t in nginx_tasks)

    def it_returns_the_source_for_the_play(instances_play):
        source = instances_play.get_source()
        assert isinstance(source, dict)
        assert source['name'] == 'instances'
        assert source['hosts'] == LOCALHOST
        assert source['connection'] == CONNECTION_LOCAL
        assert not source['gather_facts']
        assert source['remote_user'] == DEPLOYMENT_USER
        assert not source['check_mode']
        # mitogen is not enabled by default
        assert source['strategy'] == STRATEGY_MITOGEN_LINEAR
        assert source['become_method'] == BECOME_METHOD_SUDO
        assert source['tasks']
        assert isinstance(source['tasks'], list)
        assert len(source['tasks']) == 1
        assert source['tasks'][0]['action'] == 'include_role'
        assert source['tasks'][0]['args'] == {'name': 'instances'}


def describe_playbook():
    @pytest.fixture
    def prep_config():
        return OPERATIONS.contents['deployment']['steps'][0]

    @pytest.fixture
    def core_config():
        return OPERATIONS.contents['deployment']['steps'][1]

    def it_initializes_properly(prep_config, project, state):
        allow(state).save.and_return(True)
        playbook = Playbook(prep_config, project, state)
        assert isinstance(playbook, Playbook)

    def it_returns_the_rolenames(core_config, project, state):
        allow(state).save.and_return(True)
        playbook = Playbook(core_config, project, state)
        assert isinstance(playbook.rolenames, list)
        assert sorted(playbook.rolenames) == ['instances', 'ssl']

    def it_returns_the_plays(core_config, project, state):
        allow(state).save.and_return(True)
        playbook = Playbook(core_config, project, state)
        plays, updated_roles = playbook.get_plays()
        assert isinstance(plays, list)
        assert len(plays) == 2
        assert all(isinstance(p, Play) for p in plays)
        assert isinstance(updated_roles, set)
        assert updated_roles == set(['ssl', 'instances'])

    def it_returns_whether_it_can_run_in_parallel(prep_config, core_config, project, state):
        allow(state).save.and_return(True)
        playbook = Playbook(prep_config, project, state)
        assert not playbook.can_run_in_parallel

        playbook = Playbook(core_config, project, state)
        assert playbook.can_run_in_parallel

    def it_returns_the_failure_play(core_config, project, state):
        allow(state).save.and_return(True)
        playbook = Playbook(core_config, project, state)
        failplay = playbook.get_failure_play()
        assert isinstance(failplay, Play)
        assert failplay.hosts == LOCALHOST
        assert failplay.strategy == STRATEGY_MITOGEN_PARALLEL
        assert failplay.is_local()
        src = failplay.get_source()
        assert src['name'] == 'notifications'
        assert src['hosts'] == LOCALHOST
        assert src['strategy'] == STRATEGY_MITOGEN_PARALLEL
        assert src['connection'] == CONNECTION_LOCAL
        assert not src['gather_facts']
        assert src['remote_user'] == DEPLOYMENT_USER
        assert 'tasks' in src
        assert isinstance(src['tasks'], list)
        assert len(src['tasks']) == 1
        # first task should be notifications
        assert sorted(list(src['tasks'][0].keys())) == ['action', 'args', 'vars']
        assert src['tasks'][0]['action'] == 'include_role'
        assert src['tasks'][0]['args'] == {'name': 'notifications'}


def describe_playbook_iterator():
    def it_initializes_the_iterator(project, state):
        allow(state).save.and_return(True)
        iterator = PlaybookIterator('deployment', project, state)
        assert isinstance(iterator, PlaybookIterator)
        assert len(iterator) == 10

    def it_initializes_the_iterator_when_state_is_empty(project):
        state = State()
        allow(state).save.and_return(True)
        iterator = PlaybookIterator('deployment', project, state)
        assert isinstance(iterator, PlaybookIterator)
        assert iterator.operation == 'deployment'

    def it_iterates_through_the_playbooks(playbook_iterator):
        assert all((isinstance(pb, Playbook) for pb in playbook_iterator))

    def it_returns_a_playbook_in_a_specific_index(playbook_iterator):
        playbook = playbook_iterator[3]
        assert isinstance(playbook, Playbook)
        assert playbook.config['name']
        another = playbook_iterator[5]
        assert another.config['name']
        assert playbook.config['name'] != another.config['name']

    def it_applies_the_state_changes(playbook_iterator, worker_facts):
        playbook = next((pb for pb in iter(playbook_iterator) if 'workers' in pb.rolenames), None)
        assert isinstance(playbook, Playbook)
        assert 'workers' in playbook.rolenames

        # our current state doesn't have workers in it
        allow(playbook_iterator.state).save.and_return(True)
        assert not playbook_iterator.state.contents.get('workers')
        playbook_iterator.apply_state_changes(worker_facts)
        resources = worker_facts[0]['resources']
        assert playbook.state.contents['workers'] == resources

    def it_does_not_overwrite_the_credentials(playbook_iterator, database_facts):
        playbook = next((pb for pb in iter(playbook_iterator) if 'databases' in pb.rolenames), None)
        assert isinstance(playbook, Playbook)
        assert 'databases' in playbook.rolenames

        # our current state already has databases stored
        allow(playbook_iterator.state).save.and_return(True)
        assert playbook_iterator.state.contents.get('databases')
        playbook_iterator.apply_state_changes(database_facts)
        resources = database_facts[0]['resources']
        updated_resources = playbook_iterator.state.contents['databases']
        assert updated_resources == resources

        # remove credentials from the facts
        updated_resources = []
        for res in database_facts[0]['resources']:
            res['output'].update({
                'username': None,
                'password': '',
                'root_username': False,
                'root_password': None,
            })

            updated_resources.append(res)

        database_facts[0].update({'resources': updated_resources})

        # We haven't changed anything besides the credentials (that shouldn't be overwritten)
        # which means we shouldn't be able to notice anything different
        playbook_iterator.apply_state_changes(database_facts)
        allow(playbook_iterator.state).save.and_return(True)
        assert playbook_iterator.state.contents['databases'] == database_facts[0]['resources']

        # now change the usernames and passwords, things should change
        previous_resources = copy.deepcopy(updated_resources)
        updated_resources = []
        for res in database_facts[0]['resources']:
            res['output'].update({
                'username': 'some-username',
                'password': 'password12345',
                'root_username': 'RootUserName1',
                'root_password': 'RootPassw0rd1',
            })

            updated_resources.append(res)

        database_facts[0].update({'resources': updated_resources})
        assert previous_resources != updated_resources
        assert playbook.state.contents['databases'] != previous_resources
        assert playbook.state.contents['databases'] == updated_resources

    def it_doesnt_add_a_second_resource_when_a_dependency_updates(playbook_iterator):
        """
        Bug fix: when marking a resource as touched and updating facts for it,
                 we need to make sure we don't add a second resource
        """
        allow(playbook_iterator.state).save.and_return(True)

        playbook = next(pb for pb in iter(playbook_iterator) if pb.config['group'] == 'targets')
        assert isinstance(playbook, Playbook)

        # mark the dependencies for the 'instances' role as touched
        updated_roles = {'instances'}

        # keep the initial values
        mock_db_facts = [
            {'resources': playbook_iterator.state.get('databases'), 'role': 'databases'},
        ]

        mock_cache_facts = [
            {'resources': playbook_iterator.state.get('caches'), 'role': 'databases'},
        ]

        initial_databases = [r.id for r in playbook_iterator.state.get_resources('databases').all]
        initial_caches = [r.id for r in playbook_iterator.state.get_resources('caches').all]

        playbook.mark_dependants_as_touched('instances')

        plays, updated_roles = playbook.get_plays(updated_roles=updated_roles)

        assert all(r.touched for r in playbook_iterator.state.get_resources('databases').all)

        # make sure nothing changed already
        db_changes = [r.id for r in playbook_iterator.state.get_resources('databases').all]
        cache_changes = [r.id for r in playbook_iterator.state.get_resources('caches').all]

        assert db_changes == initial_databases
        assert cache_changes == initial_caches

        # apply the facts
        playbook_iterator.apply_state_changes(mock_db_facts)
        playbook_iterator.commit_state()

        db_changes = [r.id for r in playbook_iterator.state.get_resources('databases').all]
        cache_changes = [r.id for r in playbook_iterator.state.get_resources('caches').all]
        assert db_changes == initial_databases
        assert cache_changes == initial_caches


#
# Real application examples below
#
# They are either interrupted or non-deployed projects
# to serve as the edge cases for playbook testing
#
def describe_sinatra_example_interrupted():
    @pytest.fixture
    def sinatra_iterator():
        return get_playbook_iterator('sinatra-project')

    def it_returns_the_correct_playbook_for_interrupted_deployments(sinatra_iterator):
        # This example demonstrates an interrupted state.
        # The deployed parts are instances, prepare, prerequisites, ssl
        _plays, roles = get_plays_and_roles(sinatra_iterator)

        expected_roles = {
            'project', 'environment', 'nginx',
            'ruby', 'appservers', 'prepare', 'essentials',
        }

        assert roles == expected_roles

    def it_returns_the_correct_inventory(sinatra_iterator):
        playbook = next(sinatra_iterator)
        inventory = playbook.get_inventory()
        assert inventory
        assert set(inventory.keys()) == set(['all', 'application', 'provisionables'])
        assert all(re.match(r'[0-9\.]+', h) for h in inventory['all'].keys())
        assert all(re.match(r'[0-9\.]+', h) for h in inventory['application'].keys())
        assert all(re.match(r'[0-9\.]+', h) for h in inventory['provisionables'].keys())


def describe_sinatra_example_deployment():
    @pytest.fixture
    def sinatra_iterator():
        return get_playbook_iterator('sinatra-deployed')

    def it_returns_the_correct_playbook_for_interrupted_deployments(sinatra_iterator):
        _plays, roles = get_plays_and_roles(sinatra_iterator)
        # nginx is on a different version which means that we need to re-deploy
        assert roles == {'ruby', 'appservers', 'project', 'prepare', 'nginx', 'environment'}


def describe_static_site_deployment():
    @pytest.fixture
    def static_site_iterator():
        return get_playbook_iterator('static-site-undeployed')

    def it_deploys_the_static_site(static_site_iterator):
        _plays, roles = get_plays_and_roles(static_site_iterator)
        assert roles == {'prerequisites', 'prepare', 'ssl', 'elasticstorage', 'project'}

def describe_django_deployment():
    @pytest.fixture
    def django_site_iterator():
        return get_playbook_iterator('django-undeployed')

    def it_deploys_the_django_site(django_site_iterator):
        plays, roles = get_plays_and_roles(django_site_iterator)

        expected_roles = {
            'prepare', 'prerequisites', 'instances', 'ssl',
            'databases', 'essentials', 'nginx', 'python',
            'environment', 'appservers', 'project', 'routing',
            'instances', 'databases', 'ssl', 'notifications',
        }

        # pylint: disable=protected-access
        assert all(p._global_vars['is_on_preview_domain'] is False for p in plays)
        assert roles == expected_roles


def describe_django_preview_domain():
    @pytest.fixture
    def django_preview_iterator():
        return get_playbook_iterator('django-preview-domain')

    def it_returns_that_we_are_on_custom_domain(django_preview_iterator):
        plays, _roles = get_plays_and_roles(django_preview_iterator)
        # pylint: disable=protected-access
        assert all(p._global_vars['is_on_preview_domain'] for p in plays)


def describe_rails_redeployment():
    @pytest.fixture
    def rails_site_iterator():
        return get_playbook_iterator('rails-fully-deployed')

    def it_deploys_the_rails_site(rails_site_iterator):
        _plays, roles = get_plays_and_roles(rails_site_iterator)

        expected_roles = {'project', 'workers', 'prepare',
                          'appservers', 'nodejs', 'environment'}

        assert roles == expected_roles
