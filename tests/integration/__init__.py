# -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915,W0702,R0902
import os
import sys
import json
import requests
from git import Repo
from doubles import allow
from stackmate.operations import DeploymentOperation
from stackmate.ansible.plugins.callback.output import CallbackModule as StackmateOutput
from stackmate.constants import ENV_PUBLIC_KEY, ENV_STACKMATE_OPERATION_ID, ENV_PRIVATE_KEY, \
                                TASK_ACTION_FAILURE, ENV_MITOGEN_PATH


class DepoymentIntegrationTest:
    def __init__(self, directory, domain, **kwargs):
        self._directory = directory
        self._operation_id = os.environ.get(ENV_STACKMATE_OPERATION_ID, '1000')
        self._repository = Repo(os.path.realpath(os.path.join(directory, '..')))
        self._branch = kwargs.get('branch')
        self._capsys = kwargs.get('capsys')
        self._pytestcfg = kwargs.get('pytestconfig')
        self._domain = domain
        self._dump = kwargs.get('dump')
        self.operation = None

        os.environ[ENV_PRIVATE_KEY] = os.path.join(os.getcwd(), \
            'tests', 'data', 'ssh-keys', 'stackmate.key')

        os.environ[ENV_PUBLIC_KEY] = os.path.join(os.getcwd(), \
            'tests', 'data', 'ssh-keys', 'stackmate.key.pub')

        self._operation_data = {
            'operation_id': self._operation_id,
            'operation_url': f'https://stackmate.io/operations/{self._operation_id}',
            'path': directory,
            'stage': 'production',
        }

        self._commits = list(
            self._repository.iter_commits(self._branch))

        if len(self._commits) < 2:
            raise ValueError('The repository should have at least 2 commits')

    def first_deployment(self, commits_back=0):
        return self._run_operation(commits_back)

    def head_commit_deployment(self):
        return self._run_operation(0)

    def terminate(self):
        # Get the state & mark everything as tainted
        pass

    @property
    def output(self):
        """Returns the operation's output"""
        if not self.operation:
            raise ValueError('Operation is None at this point')

        return self.operation.output

    def succeeded(self):
        """Checks if there's a failure task in the list of results"""
        return not any(
            t.get('action') == 'fail' and t['status'] == TASK_ACTION_FAILURE for t in self.output
        )

    def get_role_output(self, rolename):
        """Return a specific task output"""
        return list(filter(lambda t: t.get('rolename') == rolename, self.output))

    def is_site_up(self):
        """Returns whether the site specified is up"""
        try:
            res = requests.head('https://{}'.format(self._domain), timeout=1, allow_redirects=True)
            return res.status_code == 200
        except:
            return False

    def get_site_contents(self, url='/'):
        """Returns the content for a specific page"""
        try:
            res = requests.get('https://{}/{}'.format(self._domain, url.lstrip('/')))
            return res.json() if 'json' in res.headers['content-type'] else res.text
        except:
            return False

    def _run_operation(self, commits_back=0):
        commit = self._commits[commits_back:][0]
        attrs = self._operation_data.copy()

        attrs.update({
            'is_first_deployment': True,
            'commit_reference': str(commit),
            'commit_author':str(commit.author),
            'commit_message': str(commit.message),
        })

        self.operation = DeploymentOperation(**attrs)

        capmanager = None
        if self._pytestcfg:
            capmanager = self._pytestcfg.pluginmanager.getplugin('capturemanager')

            if capmanager.is_globally_capturing():
                capmanager.suspend_global_capture()

        if self._dump:
            self.operation.dump()
        else:
            self.operation.run()

        if capmanager:
            capmanager.resume_global_capture()

        return self.output, self.operation
