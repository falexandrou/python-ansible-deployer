# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915
from stackmate.project import Project, PROJECT_FLAVOR_INSTANCES
from stackmate.configurations import ProjectConfiguration
from stackmate.deployables import Deployable
from stackmate.state import State

def describe_project():
    def it_initializes_when_a_configuration_is_passed(project_config, vault):
        project = Project(configuration=project_config, vault=vault)
        assert isinstance(project, Project)
        assert isinstance(project.configuration, ProjectConfiguration)

    def it_loads_the_project_from_file(project_path, stage):
        project = Project.load(project_path, stage)
        assert isinstance(project, Project)
        assert isinstance(project.configuration, ProjectConfiguration)

    def it_has_all_the_attributes_set(project, project_config, vault):
        project = Project(configuration=project_config, vault=vault)
        assert hasattr(project, 'framework')
        assert hasattr(project, 'flavor')
        assert hasattr(project, 'repository')
        assert hasattr(project, 'notifications')
        assert hasattr(project, 'user')
        assert hasattr(project, 'documentroot')
        assert hasattr(project, 'providers')
        assert hasattr(project, 'provider')
        assert hasattr(project, 'region')
        assert hasattr(project, 'branch')
        assert hasattr(project, 'domain')
        assert hasattr(project, 'pipeline')
        assert hasattr(project, 'services')

        config_contents = project_config.contents
        assert project.flavor == PROJECT_FLAVOR_INSTANCES
        assert project.framework == config_contents.framework
        assert project.branch == config_contents.branch
        assert project.notifications == config_contents.notifications
        assert project.user == config_contents.user
        assert project.documentroot == config_contents.documentroot
        assert project.domain == config_contents.domain
        assert project.provider == config_contents.provider
        assert project.region == config_contents.region
        assert len(project.pipeline) == len(config_contents.pipeline)

    def it_provides_a_path_property(project_config, vault):
        project = Project(configuration=project_config, vault=vault)
        assert hasattr(project, 'path')
        assert project.path == project_config.path

    def it_serializes_the_project_properly(project):
        serialized = project.serialize()
        assert serialized['branch']
        assert serialized['branch'] == project.branch

        assert serialized['documentroot']
        assert serialized['documentroot'] == project.documentroot

        assert serialized['provider']
        assert serialized['provider'] == project.provider

        assert serialized['region']
        assert serialized['region'] == project.region

        assert serialized['framework']
        assert serialized['framework'] == project.framework

        assert serialized['pipeline']

    def it_returns_the_deployables_for_the_project(project):
        deployables = project.deployables
        assert isinstance(deployables, list)
        assert deployables
        assert all(isinstance(dp, Deployable) for dp in deployables)
