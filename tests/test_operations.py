"""Provides tests for operations"""
# -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915
from stackmate.operations import DeploymentOperation, RollbackOperation
from stackmate.playbooks import PlaybookIterator


def describe_deployment_operation():
    def get_deployment_attrs(project_path, stage):
        return {
            'operation_id': '123',
            'operation_url': 'https://stackmate.io/operations/123',
            'path': project_path,
            'stage': stage,
            'is_first_deployment': True,
            'commit_reference': 'abc12345',
            'commit_author': 'John Doe',
            'commit_message': 'Commit message',
        }

    def it_instantiates_and_validates_the_deployment_operation(project_path, stage):
        deployment_attrs = get_deployment_attrs(project_path, stage)
        operation = DeploymentOperation(**deployment_attrs)

        assert isinstance(operation, DeploymentOperation)
        assert operation.operation_id == deployment_attrs['operation_id']
        assert operation.operation_url == deployment_attrs['operation_url']
        assert operation.path == project_path
        assert operation.stage == stage
        assert operation.is_first_deployment is True
        assert operation.commit_reference == deployment_attrs['commit_reference']
        assert operation.commit_author == deployment_attrs['commit_author']
        assert operation.commit_message == deployment_attrs['commit_message']

    def it_provides_the_variables_to_the_playbook(project_path, stage):
        deployment_attrs = get_deployment_attrs(project_path, stage)
        operation = DeploymentOperation(**deployment_attrs)

        assert isinstance(operation, DeploymentOperation)
        assert deployment_attrs['operation_id']
        assert operation.operation_id == deployment_attrs['operation_id']
        assert 'operation_id' in operation.iterator.extra_vars
        assert operation.iterator.extra_vars['operation_id'] == deployment_attrs['operation_id']

        assert deployment_attrs['operation_url']
        assert operation.operation_url == deployment_attrs['operation_url']
        assert 'operation_url' in operation.iterator.extra_vars
        assert operation.iterator.extra_vars['operation_url'] == deployment_attrs['operation_url']

    def it_validtes_the_operation(project_path, stage):
        deployment_attrs = get_deployment_attrs(project_path, stage)
        operation = DeploymentOperation(**deployment_attrs)
        assert operation.validate()

    def it_returns_the_playbook_iterator(project_path, stage):
        deployment_attrs = get_deployment_attrs(project_path, stage)
        operation = DeploymentOperation(**deployment_attrs)
        iterator = operation.iterator
        assert isinstance(iterator, PlaybookIterator)
        assert iterator.operation == 'deployment'


def describe_rollback_operation():
    def get_rollback_attrs(project_path, stage):
        return {
            'operation_id': '123',
            'operation_url': 'https://stackmate.io/operations/123',
            'path': project_path,
            'stage': stage,
            'steps': 2,
        }


    def it_instantiates_and_validates_the_rollback_operation(project_path, stage):
        rollback_attrs = get_rollback_attrs(project_path, stage)
        operation = RollbackOperation(**rollback_attrs)

        assert isinstance(operation, RollbackOperation)
        assert operation.operation_id == rollback_attrs['operation_id']
        assert operation.operation_url == rollback_attrs['operation_url']
        assert operation.path == project_path
        assert operation.stage == stage
        assert operation.steps is rollback_attrs['steps']

    def it_validtes_the_operation(project_path, stage):
        rollback_attrs = get_rollback_attrs(project_path, stage)
        operation = RollbackOperation(**rollback_attrs)
        assert operation.validate()

    def it_returns_the_playbook_iterator(project_path, stage):
        rollback_attrs = get_rollback_attrs(project_path, stage)
        operation = RollbackOperation(**rollback_attrs)
        iterator = operation.iterator
        assert isinstance(iterator, PlaybookIterator)
        assert iterator.operation == 'rollback'
