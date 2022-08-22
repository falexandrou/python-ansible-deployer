"""Ansible integration"""
# -*- coding: utf-8 -*-
import os

from ansible.playbook.play import Play as AnsiblePlay
from ansible.vars.manager import VariableManager as AnsibleVariableManager
from ansible.inventory.manager import InventoryManager as AnsibleInventoryManager
from ansible.executor.task_queue_manager import TaskQueueManager as AnsibleTaskQueueManager
from stackmate.constants import STACKMATE_STATE_FACT
from stackmate.configurations import ConfigurationFile
from stackmate.deployables.service import Service


class Configuration(ConfigurationFile):
    """
    Configuration file that provides default ansible configurations
    """
    def __init__(self):
        super().__init__(
            rootpath=os.path.join(os.getcwd(), 'stackmate', 'config'), \
            filename='ansible.yml')


class InventoryManager(AnsibleInventoryManager):
    """
    Wrapper for Ansible's inventory manager

    @see ansible.inventory.manager.InventoryManager
    """
    def parse_sources(self, cache=False):
        # Suppress warnings for missing inventory files
        return True

    def set_inventory(self, inventory):
        """Sets the inventory as a dictionary"""
        for group, hosts in inventory.items():
            if not group in self._inventory.groups:
                self._inventory.add_group(group)

            for host in hosts:
                self._inventory.add_host(host, group)

        return self


class TaskQueueManager(AnsibleTaskQueueManager):
    """
    Wrapper for Ansible's TaskQueueManager

    @see ansible.executor.task_queue_manager.TaskQueueManager
    """
    def add_callback_plugin(self, plugin):
        """
        Adds a callback plugin
        """
        self._callback_plugins.append(plugin)

    @property
    def inventory(self):
        """
        Returns the inventory for the task queue manager
        """
        return self._inventory


class VariableManager(AnsibleVariableManager):
    """
    Wrapper for Ansible's variable manager
    """
    def get_non_persistent_facts(self):
        """
        Returns the non persistent facts
        """
        return self._nonpersistent_fact_cache

    def get_state_facts(self):
        """
        Returns the facts that that were generated during the consequent
        role executions
        """
        state = []

        for hostfacts in self.get_non_persistent_facts().values():
            if STACKMATE_STATE_FACT in hostfacts:
                state += hostfacts[STACKMATE_STATE_FACT]

        return state


class Play(AnsiblePlay):
    """
    Wrapper for Ansible's Play class
    """
