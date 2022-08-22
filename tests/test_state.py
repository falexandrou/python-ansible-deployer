# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915
import pytest
from doubles import allow
from stackmate.state import State

def describe_state():
    @pytest.fixture
    def project_state(project_path, stage):
        state = State(rootpath=project_path, stage=stage)
        allow(state).save.and_return(True)
        return state

    def it_initializes_correctly(project_state):
        assert isinstance(project_state, State)
        assert project_state.contents

    def it_resolves_paths_within_the_state(project_state):
        assert project_state.get('project')
        assert not project_state.get('DOESNOTEXIST')

    def it_updates_certain_attributes_for_resources(project_state):
        assert project_state.get('project')
        project_entry = project_state.get('project')
        prevlen = len(project_entry)
        assert prevlen == 1
        assert not any(e.get('touched') for e in project_entry)

        project_state.merge_role_resource_attributes('project', touched=True)
        assert project_state.get('project')
        assert len(project_state.get('project')) == 1
        assert all(e.get('touched') for e in project_state.get('project'))

    def it_updates_paths_within_the_state(project_state, database_facts):
        assert project_state.contents.get('databases') != database_facts
        project_state.update('databases', database_facts)
        assert len(project_state.contents.get('databases')) == 1
        assert project_state.contents.get('databases') == database_facts

    def it_performs_multiple_state_manipulations(project_state, database_facts):
        project_state.update('databases', database_facts)
        assert len(project_state.contents.get('databases')) == 1
        assert all(not r['touched'] for r in project_state.contents.get('databases'))
        project_state.merge_role_resource_attributes('databases', touched=True)
        assert all(r['touched'] for r in project_state.contents.get('databases'))
        assert len(project_state.contents.get('databases')) == 1

    def it_saves_the_state(project_state, database_facts):
        project_state.update('databases', database_facts)
        assert len(project_state.contents.get('databases')) == 1
        project_state.save()
        assert len(project_state.contents.get('databases')) == 1
