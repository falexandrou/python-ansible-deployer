"""Provides JSON callback support"""
# -*- coding: utf-8 -*-
import os
import json
import sys
import uuid
import logging
from datetime import datetime
from ansible.plugins.callback import CallbackBase
from ansible.parsing.ajson import AnsibleJSONEncoder
from ansible.vars.clean import strip_internal_keys, module_response_deepcopy
from stackmate.constants import TASK_ACTION_START, TASK_ACTION_SUCCESS, TASK_ACTION_SKIP, \
                                TASK_ACTION_FAILURE, LOCALHOST, ENV_STACKMATE_OPERATION_ID, \
                                OUTPUT_TYPE_DEPLOYMENT, OUTPUT_TYPE_GROUP, OUTPUT_TYPE_TASK, \
                                IGNORE_EMPTY_OUTPUT_TAG, LIVE_OUTPUT_TAG, COMMAND_VAR_TAG

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

SKIPPED_RESULT_KEYS = ['changed', 'diff']

DOCUMENTATION = '''
Provides the playbook output as a JSON
'''


class CallbackModule(CallbackBase):
    """Callback module for ansible 2.8+"""
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'stdout'
    CALLBACK_NAME = 'stackmate_output'

    def __init__(self, display=None):
        super(CallbackModule, self).__init__(display)
        self.results = []
        self._session = str(uuid.uuid1())
        self._group_id = None
        self._task_start = datetime.utcnow()
        self._operation_id = os.environ.get(ENV_STACKMATE_OPERATION_ID)
        self._play_context = None

    def set_play_context(self, play_context):
        """Sets the play context"""
        self._play_context = play_context

    def write(self, result):
        """Write output to stdout"""
        self.results.append(result)
        print(json.dumps(result, cls=AnsibleJSONEncoder))

    def explicit_deployment_output(self, status, **kwargs):
        """Logs explicit deployment output"""
        output = dict(
            type=OUTPUT_TYPE_DEPLOYMENT,
            status=status,
            operation_id=self._operation_id,
            datetime_utc=datetime.utcnow(),
            **kwargs,
        )

        self.write(output)

    def _play_started(self, play, **kwargs):
        """Play started"""
        # pylint: disable=unused-argument,protected-access
        self._group_id = str(uuid.uuid1())

        output = dict(
            type=OUTPUT_TYPE_GROUP,
            group_id=self._group_id,
            name=play.name,
            operation_id=self._operation_id,
            datetime_utc=datetime.utcnow(),
        )

        self.write(output)

    def _task_started(self, host, task):
        """Task Started"""
        # pylint: disable=protected-access

        # we explicitly asked to ignore the output of this command
        if IGNORE_EMPTY_OUTPUT_TAG in task.tags:
            return

        # also ignore the live output task
        if LIVE_OUTPUT_TAG in task.tags:
            return

        self._task_start = datetime.utcnow()
        hostname = host.name if host.name != LOCALHOST else None
        taskname = 'liveoutput' if LIVE_OUTPUT_TAG in task.tags else task.name

        rolename = None
        if task._role:
            rolename = task._role.get_name()
            if task._role.get_parents():
                rolename = task._role.get_parents()[0].get_name()

        output = dict(
            type=OUTPUT_TYPE_TASK,
            task_uuid=task._uuid,
            group_id=self._group_id,
            name=taskname,
            operation_id=self._operation_id,
            datetime_utc=datetime.utcnow(),
            command=task.get_vars().get('command') if COMMAND_VAR_TAG in task.tags else '',
            action=task.action,
            rolename=rolename,
            host=hostname,
            status=TASK_ACTION_START,
            message=None,
            output=None,
            duration=None,
            debug={},
            tags=task.tags,
        )

        self.write(output)

    def _task_output(self, result, status):
        """Print the task's result"""
        # pylint: disable=unused-argument,protected-access
        task = result._task
        abridged_result = strip_internal_keys(module_response_deepcopy(result._result))
        message = abridged_result.get('msg', '')
        output = abridged_result.get('stdout', '') + abridged_result.get('stderr', '')

        if abridged_result.get('results'):
            message += '\n'.join([r.get('msg', '') for r in abridged_result['results']])
            output += '\n'.join([
                r.get('stdout', '') + r.get('stderr', '') for r in abridged_result['results']
            ])

        # Async poll status produces a lot of empty output
        ignore_empties = IGNORE_EMPTY_OUTPUT_TAG in task.tags or LIVE_OUTPUT_TAG in task.tags
        # We didn't get output from the live output watch task, ignore
        if ignore_empties and not output and not message:
            return

        reason = ''
        command = ''
        hostname = result._host.name if result._host.name != LOCALHOST else None

        if isinstance(abridged_result.get('cmd'), str):
            command = abridged_result['cmd']

        # overwrite the command in this task with the actual command that is being executed
        if COMMAND_VAR_TAG in task.tags:
            command = task.get_vars().get('command')

        if status == TASK_ACTION_FAILURE:
            reason = abridged_result.get('reason', '')
        elif status == TASK_ACTION_SKIP:
            reason = abridged_result.get('skip_reason', '')

        # print out debug messages
        if result._task.action == 'debug':
            self.write(dict(
                type='debug',
                group_id=self._group_id,
                operation_id=self._operation_id,
                output={k:v for k, v in abridged_result.items() if k not in SKIPPED_RESULT_KEYS}))

        processed = dict(
            type=OUTPUT_TYPE_TASK,
            task_uuid=task._uuid,
            group_id=self._group_id,
            name=task.name,
            datetime_utc=datetime.utcnow(),
            operation_id=self._operation_id,
            # task - related attributes
            action=result._task.action,
            rolename=task._role.get_name() if task and task._role else None,
            host=hostname,
            status=status,
            reason=reason,
            command=command,
            message=message.strip() if isinstance(message, str) else message,
            output=output.strip() if isinstance(output, str) else output,
            duration=str(datetime.utcnow() - self._task_start),
            tags=task.tags,
            debug=dict(
                verbose=abridged_result.get('result'),
                exception=abridged_result.get('exception'),
                invocation=abridged_result.get('invocation'),
            ),
        )

        self.write(processed)

    def v2_runner_on_ok(self, result):
        """Task succeeded"""
        return self._task_output(result, TASK_ACTION_SUCCESS)

    def v2_runner_on_failed(self, result, ignore_errors=False):
        """Task failed"""
        # pylint: disable=unused-argument
        return self._task_output(result, TASK_ACTION_FAILURE)

    def v2_runner_on_skipped(self, result):
        """Task was skipped"""
        return self._task_output(result, TASK_ACTION_SKIP)

    v2_playbook_on_play_start = _play_started
    v2_runner_on_start = _task_started
    v2_runner_on_unreachable = v2_runner_on_failed

    # Adding the full list of callbacks as placeholders
    # v2_playbook_on_start = _task_output
    # v2_on_any = _task_output
    # v2_runner_on_failed = _task_output
    # v2_runner_on_skipped = _task_output
    # v2_runner_on_unreachable = _task_output
    # v2_runner_on_async_poll = _task_output
    # v2_runner_on_async_ok = _task_output
    # v2_runner_on_async_failed = _task_output
    # v2_playbook_on_notify = _task_output
    # v2_playbook_on_no_hosts_matched = _task_output
    # v2_playbook_on_no_hosts_remaining = _task_output
    # v2_playbook_on_task_start = _task_output
    # v2_playbook_on_cleanup_task_start = _task_output
    # v2_playbook_on_handler_task_start = _task_output
    # v2_playbook_on_vars_prompt = _task_output
    # v2_playbook_on_import_for_host = _task_output
    # v2_playbook_on_not_import_for_host = _task_output
    # v2_playbook_on_stats = _task_output
    # v2_on_file_diff = _task_output
    # v2_playbook_on_include = _task_output
    # v2_runner_item_on_skipped = _task_output
    # v2_runner_retry = _task_output
    # v2_runner_on_start = _task_output
