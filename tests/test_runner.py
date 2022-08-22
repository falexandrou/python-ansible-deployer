# -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915,R0201,R0903,W0106
import pytest
from doubles import allow
from stackmate.runner import Runner
from stackmate.project import Project
from stackmate.state import State
from stackmate.playbooks import PlaybookIterator
from stackmate.exceptions import DeploymentFailedError


def mock_runner(play, _inventory, _output_logger):
    return [{'role': play.rolename, 'resources': []}]


def mock_runner_failing_nginx(play, _inventory, _output_logger):
    if play.rolename == 'nginx':
        raise DeploymentFailedError
    return [{'role': play.rolename, 'resources': []}]


def mock_runner_failing_databases(play, _inventory, _output_logger):
    if play.rolename == 'databases':
        raise DeploymentFailedError
    return [{'role': play.rolename, 'resources': []}]


def describe_runner():
    @pytest.fixture
    def iterator(project_path, stage):
        proj = Project.load(rootpath=project_path, stage=stage)
        state = State()
        allow(state).save.and_return(True)
        return PlaybookIterator('deployment', proj, state)

    @pytest.fixture
    def runner(iterator):
        return Runner(iterator)

    def it_dumps_the_playbook_without_errors(iterator):
        runner = Runner(iterator)
        runner.dump()

    def it_runs_the_playbook(runner):
        # plays, inventories, mock_runner = get_mock_runner_components()

        # run!
        assert not runner.iterator.state.contents.keys()
        runner.run(process_func=mock_runner, commit_state=False)

        assert len(runner.iterator.state.contents.keys()) == 21
        assert set(runner.iterator.state.contents.keys()) == {
            'appservers', 'caches', 'cdn', 'configfiles', 'databases',
            'elasticstorage', 'environment', 'essentials', 'instances',
            'jobschedules', 'mailer', 'nginx', 'notifications', 'prepare',
            'prerequisites', 'project', 'routing', 'ruby', 'ssl',
            'volumes', 'workers',
        }

    def it_stops_when_an_error_is_thrown_on_sequential_execution(runner):
        # Make the nginx play fail. The reason for that is that nginx is being executed
        # on a non-parallel playbook, so we need to make sure that the _run_plays_sequentially
        # method, will catch the error and prevent later plays from being run

        # mock the runner to return a non-error "0" status code
        assert not runner.iterator.state.contents.keys()
        runner.run(process_func=mock_runner_failing_nginx, commit_state=False)

        provisioned = set(runner.iterator.state.contents.keys())
        assert len(provisioned) == 11 # 10 plays + the failure one
        assert 'nginx' not in provisioned
        assert provisioned == {
            'prepare', 'prerequisites', 'ssl', 'instances', 'essentials',
            'caches', 'cdn', 'databases', 'mailer', 'elasticstorage', 'volumes',
        }

    def it_stops_on_generic_error(runner):
        # It should be able to handle any exception without raising it
        # It should however print the output with deployment failed
        allow(runner).process.and_raise(ValueError)
        runner.run(process_func=mock_runner, commit_state=False)

    def it_stops_when_an_error_is_thrown_on_parallel_execution(runner):
        # Make the databases play fail. The reason for that is that 'databses' is being executed
        # on a **parallel** playbook, so we need to make sure that the _run_plays_in_parallel
        # method, will catch the error and prevent later plays from being run

        assert not runner.iterator.state.contents.keys()
        runner.run(process_func=mock_runner_failing_databases, commit_state=False)
        provisioned = set(runner.iterator.state.contents.keys())

        assert len(provisioned) == 10 # 9 plays + the failure one
        assert provisioned == {
            'prepare', 'prerequisites', 'ssl', 'instances',
            'essentials', 'caches', 'mailer', 'cdn',
            'elasticstorage', 'volumes',
        }
