"""Runs automatically generated playbooks"""
# -*- coding: utf-8 -*-
import os
import sys
import traceback
from collections import namedtuple
from concurrent.futures import ProcessPoolExecutor, as_completed
from ansible import constants as C
from ansible.config.manager import ConfigManager
from ansible.parsing.dataloader import DataLoader
from ansible.plugins.loader import strategy_loader
from stackmate.helpers import list_chunks
from stackmate.exceptions import DeploymentFailedError
from stackmate.ansible.plugins.callback.output import CallbackModule as StackmateOutput
from stackmate.ansible import Play, Configuration as AnsibleConfiguration,\
                              VariableManager, InventoryManager, TaskQueueManager
from stackmate.constants import ENV_MITOGEN_PATH, DEPLOYMENT_STARTED, \
                                DEPLOYMENT_SUCCESS, DEPLOYMENT_FAILURE, \
                                ANSIBLE_FORKS_NUM


Setting = namedtuple('Setting', 'name value')
ANSIBLE_DEFAULTS = AnsibleConfiguration().contents.get('default_config')



def init_ansible_configuration():
    """Initializes ansible configuration & generates the constants required"""
    # Load the defaults we've defined under 'stackmate/config/ansible.yml'
    custom_settings = []
    config = ConfigManager()


    if ANSIBLE_DEFAULTS:
        for (name, value) in ANSIBLE_DEFAULTS.items():
            C.set_constant(name, value)
            custom_settings.append(Setting(name=name, value=value))

    # Add our custom roles path
    role_paths = config.data.get_setting('DEFAULT_ROLES_PATH').value
    role_paths.append(os.path.join(os.getcwd(), 'stackmate', 'ansible', 'roles'))

    # Add the value to our custom settings
    custom_settings.append(Setting(name='DEFAULT_ROLES_PATH', value=role_paths))

    # mitogen integration
    if os.environ.get(ENV_MITOGEN_PATH):
        strategy_loader.add_directory(
            os.path.realpath(os.environ.get(ENV_MITOGEN_PATH)), with_subdir=False)

    # update the configuration with custom settings
    for setting in custom_settings:
        config.data.update_setting(setting)

    # set the configuration
    for setting in config.data.get_settings():
        C.set_constant(setting.name, setting.value)


def run_play(play, inventory, output_logger):
    """Runs a play"""
    init_ansible_configuration()

    loader = DataLoader()
    inventory_manager = InventoryManager(loader=loader).set_inventory(inventory)
    variable_manager = VariableManager(loader=loader, inventory=inventory_manager)

    tqm = TaskQueueManager(
        inventory=inventory_manager,
        variable_manager=variable_manager,
        loader=loader,
        forks=ANSIBLE_FORKS_NUM,
        passwords={}, # TODO
        stdout_callback=output_logger,
    )

    runnable = Play.load(
        play.get_source(),
        vars=play.get_variables(),
        variable_manager=variable_manager,
        loader=loader)

    exit_code = tqm.run(runnable)
    tqm.cleanup()

    if int(exit_code) != 0:
        raise DeploymentFailedError

    return variable_manager.get_state_facts()


def dump_output(play, _inventory, output_logger):
    """Mock the run_play function"""
    output_logger.explicit_deployment_output(
        'print', name=play.playname, hosts=play.hosts, strategy=play.strategy)

    return [{'role': play.rolename, 'resources': []}]


class Runner:
    """Generates files required by ansible and runs the playbook"""
    def __init__(self, iterator, json_output=True):
        self.iterator = iterator
        self.output_logger = StackmateOutput() if json_output else None

    def dump(self):
        """Prints out the entire playbook (for debugging purposes)"""
        self.run(process_func=dump_output, commit_state=False)

    def log_stackmate_output(self, action, **kwargs):
        """Logs output specific to the stackmate client"""
        if not self.output_logger:
            return

        self.output_logger.explicit_deployment_output(action, **kwargs)

    def _run_plays_sequentially(self, plays, inventory, process_func, commit_state=True):
        """Runs the plays sequentially"""
        for play in plays:
            if not play.tasks:
                continue

            facts = process_func(play, inventory, self.output_logger)

            self.iterator.apply_state_changes(facts)

            if commit_state:
                self.iterator.commit_state()

    def _run_plays_in_parallel(self, plays, inventory, process_func, commit_state=True):
        """Runs the plays in parallel"""
        failures = 0
        batch_size = os.cpu_count()
        results = []
        result_objects = []

        with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
            chunks = list_chunks(plays, chunk_size=batch_size)
            futures_to_play = {}

            for chunk in chunks:
                futures_to_play.update({
                    executor.submit(
                        process_func, pp, inventory, self.output_logger): pp for pp in chunk
                })

                for future in as_completed(futures_to_play, timeout=None):
                    try:
                        facts = future.result()

                        self.iterator.apply_state_changes(facts)

                        if commit_state:
                            self.iterator.commit_state()
                    except DeploymentFailedError:
                        failures += 1

            executor.shutdown(wait=True)

        if failures > 0:
            raise DeploymentFailedError

    def run(self, process_func=None, commit_state=True):
        """Runs a series of playbooks within a try / except block that handles failures"""
        try:
            self.process(process_func=process_func, commit_state=commit_state)
        except Exception as exc: # pylint: disable=broad-except
            tback = sys.exc_info()[2]
            self.log_stackmate_output(DEPLOYMENT_FAILURE, debug={
                'exception': traceback.format_exception(type(exc), exc, tback)
            })

    def process(self, process_func=None, commit_state=True):
        """Processes the list of playbooks"""
        updated_roles = set()
        process_func = process_func or run_play
        playbooks = list(iter(self.iterator))

        # mark the deployment as started
        self.log_stackmate_output(
            DEPLOYMENT_STARTED, roles=list({r for pb in playbooks for r in pb.rolenames}))

        for playbook in playbooks:
            inventory = playbook.get_inventory()
            plays, updated_roles = playbook.get_plays(updated_roles)

            # no plays were found, provisioning probably not required, move on
            if not plays:
                continue

            try:
                if playbook.can_run_in_parallel:
                    self._run_plays_in_parallel(plays, inventory, process_func, commit_state)
                else:
                    self._run_plays_sequentially(plays, inventory, process_func, commit_state)
            except DeploymentFailedError:
                # run the special play that is notifying us about failures
                failplay = playbook.get_failure_play()

                if failplay is not None:
                    process_func(failplay, inventory, self.output_logger)

                return self.log_stackmate_output(DEPLOYMENT_FAILURE)

        return self.log_stackmate_output(DEPLOYMENT_SUCCESS)
