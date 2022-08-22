"""Provides tests for dependencies"""
# -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915

from stackmate.deployables.dependency import Dependency
from stackmate.base import Model

def describe_dependency_model():
    def it_initializes_correctly(application_service):
        dep = Dependency.factory(kind='nginx', service=application_service)
        assert isinstance(dep, Dependency)
        assert isinstance(dep, Model)
        assert hasattr(dep, 'kind')
        assert hasattr(dep, 'version')

    def it_initializes_with_kind_and_version(application_service):
        dep = Dependency.factory(
            kind='nginx', version='1.18', service=application_service)

        assert dep.kind == 'nginx'
        assert dep.version == '1.18'
        assert dep.validate()

    def it_initializes_with_kind_version_and_credentials(application_service):
        creds = dict(username='abc', password='123')
        root = dict(username='abc', password='123')
        dep = Dependency.factory(
            kind='nginx',
            version='1.18',
            credentials=creds,
            root_credentials=root,
            service=application_service)

        assert dep.kind == 'nginx'
        assert dep.version == '1.18'
        assert dep.credentials is not None
        assert dep.root_credentials is not None
        assert sorted(dep.attribute_names) == sorted([
            'configfiles', 'credentials', 'kind', 'reference', 'environment',
            'port', 'role', 'root_credentials', 'unique', 'version',
        ])

    def it_returns_the_default_version_if_not_provided(application_service):
        dep = Dependency.factory(kind='nginx', service=application_service)
        assert dep.kind == 'nginx'
        assert dep.version == '1.18'
