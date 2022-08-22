"""Provides tests for dependencies"""
# -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915
from stackmate.base import AttributeDict
from stackmate.configurations import ProjectConfiguration, ReadOnlyConfigurationFile,\
    BranchedConfiguration, ProjectState, ConfigurationFile, OperationsConfiguration


def describe_operations_configuration():
    def it_loads_the_configuration():
        cfg = OperationsConfiguration()
        assert isinstance(cfg, ReadOnlyConfigurationFile)
        assert cfg.rootpath.endswith('/stackmate/config')
        assert cfg.filename == 'operations.yml'
        assert cfg.exists
        assert cfg.contents


def describe_project_configuration():
    def it_loads_the_configuration(project_config):
        assert isinstance(project_config, ProjectConfiguration)
        assert isinstance(project_config, ReadOnlyConfigurationFile)
        assert isinstance(project_config, BranchedConfiguration)

    def it_has_the_correct_root_attributes():
        assert set(ProjectConfiguration.ROOT_ATTRIBUTES) == {
            'framework', 'repository', 'notifications',
            'provider', 'region', 'providers', 'documentroot',
        }

def describe_project_state():
    def it_loads_the_state_file(project_path, stage):
        state = ProjectState(rootpath=project_path, stage=stage)
        assert isinstance(state, ProjectState)
        assert isinstance(state, ConfigurationFile)
        assert isinstance(state, BranchedConfiguration)

    def it_has_the_correct_root_attributes():
        assert set(ProjectState.ROOT_ATTRIBUTES) == set(['version'])

    def it_updates_the_contents_properly(project_path, stage):
        state = ProjectState(rootpath=project_path, stage=stage)
        contents = state.contents
        new_version = 50000
        new_documentroot = '/tmp/nowhere'
        assert contents.get_path('version') != new_version
        assert contents.get_path('documentroot') != new_documentroot

        contents.set_path('version', new_version)
        assert contents.get_path('version') == new_version
        state.contents = contents

        assert isinstance(state.contents, AttributeDict)
        assert state.contents.get_path('version') == new_version
        assert state.contents.get_path('production.version') is None
        assert state.full_contents.get('version') == new_version
        assert state.full_contents.get('production').get('version') is None


        contents.set_path('documentroot', new_documentroot)
        assert contents.get_path('documentroot') == new_documentroot
        state.contents = contents

        assert isinstance(state.contents, AttributeDict)
        assert state.contents.get_path('documentroot') == new_documentroot
        assert state.full_contents.get('documentroot') is None
        assert state.full_contents.get('production').get('documentroot') == new_documentroot
