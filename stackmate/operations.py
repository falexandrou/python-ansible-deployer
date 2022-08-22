"""Returns the operations for playbooks"""
# -*- coding: utf-8 -*-
import pprint
from abc import ABC, abstractmethod
from stackmate.base import Model, ModelAttribute
from stackmate.playbooks import PlaybookIterator
from stackmate.runner import Runner
from stackmate.project import Project
from stackmate.state import State

class BaseOperation(Model, ABC):
    """Base operation model"""
    _operation_id = ModelAttribute(required=True, datatype=str)
    _operation_url = ModelAttribute(required=True, datatype=str)
    _path = ModelAttribute(required=True, datatype=str)
    _stage = ModelAttribute(required=True, datatype=str)
    _debug = ModelAttribute(required=False, datatype=bool, default=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._project = Project.load(rootpath=self.path, stage=self.stage)
        self._state = State(rootpath=self.path, stage=self.stage)
        self._iterator = None
        self._extra_vars = {}
        self._runner = None

    def validate(self):
        """Validates the model and the project"""
        return super().validate() and self._project.validate() and self._project.ssh_keys

    @property
    def extra_vars(self):
        """Returns the extra vars to be used in playbooks"""
        return self._extra_vars

    @property
    @abstractmethod
    def iterator(self) -> PlaybookIterator:
        """Returns the playbook for this operation"""

    def get_runner(self):
        """Returns the runner for the operation"""
        if not self._runner:
            self._runner = Runner(iterator=self.iterator)
        return self._runner

    def run(self):
        """Runs the operation"""
        self.validate()

        runner = self.get_runner()

        return runner.run() if not self.debug else pprint.pprint(runner.dump())

    def dump(self):
        """Runs the playbook"""
        self.validate()

        return self.get_runner().dump()

    @property
    def output(self):
        """Returns the output for the operation"""
        return self.get_runner().output_logger.results


class DeploymentOperation(BaseOperation):
    """The deployment operation"""
    _is_first_deployment = ModelAttribute(required=False, datatype=bool, default=False)
    _commit_reference = ModelAttribute(required=True, datatype=str)
    _commit_author = ModelAttribute(required=True, datatype=str)
    _commit_message = ModelAttribute(required=True, datatype=str)

    @property
    def extra_vars(self):
        """Returns the extra vars to be used in playbooks"""
        if not self._extra_vars:
            self._extra_vars = {
                'operation_id': self.operation_id,
                'operation_url': self.operation_url,
                'is_first_deployment': self.is_first_deployment,
                'commit': {
                    'reference': self.commit_reference,
                    'author': self.commit_author,
                    'message': self.commit_message,
                },
            }

        return self._extra_vars

    @property
    def iterator(self) -> PlaybookIterator:
        """Returns the playbook for this operation"""
        if not self._iterator:
            self._iterator = PlaybookIterator(
                'deployment', project=self._project, state=self._state, **self.extra_vars
            )

        return self._iterator


class RollbackOperation(BaseOperation):
    """The Rollback operation"""
    _steps = ModelAttribute(required=True, datatype=int, default=1)

    @property
    def extra_vars(self):
        """Returns the extra vars to be used in playbooks"""
        if not self._extra_vars:
            self._extra_vars = {'steps': self.steps}

        return self._extra_vars

    @property
    def iterator(self) -> PlaybookIterator:
        """Returns the playbook for this operation"""
        if not self._iterator:
            self._iterator = PlaybookIterator(
                'rollback', project=self._project, state=self._state, **self.extra_vars
            )

        return self._iterator
