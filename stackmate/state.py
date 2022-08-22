"""Provides handlers for the project's state"""
# -*- coding: utf-8 -*-
from stackmate.constants import VERSION, STATE_OUTPUT_PRESERVED_KEYS
from stackmate.configurations import ProjectState
from stackmate.resources import Resource, ResourceList


class State:
    """Holds the state for the project"""
    def __init__(self, rootpath=None, stage=None):
        self.__state_file = ProjectState(rootpath=rootpath, stage=stage)
        self.__version = self.__state_file.contents.pop('version', VERSION)
        self.__contents = self.__state_file.contents

    def get_resources(self, rolename: str) -> ResourceList:
        """Returns the resource list for the deployable"""
        return ResourceList(self.contents.get(rolename, []))

    def get_deployable_resources(self, deployable) -> ResourceList:
        """Returns resources for a specific deployable"""
        roleresources = self.get_resources(deployable.rolename)
        return ResourceList(resources=roleresources.find(deployable))

    def get(self, path, default=None):
        """Returns the path in the state"""
        return self.__contents.get_path(path) or default

    def merge_role_resource_attributes(self, role, **attrs):
        """Merges attributes into the ones of every resource for a given role"""
        if not self.__contents.get(role):
            return

        entries = self.__contents[role]
        for entry in entries:
            entry.update(attrs)

        self.__contents.set_path(role, entries)

    def update(self, role, content):
        """Updates a given role in the state"""
        resources = []
        currents = self.get_resources(role)

        for entry in content:
            # find the resource entry in the `current` list
            current_entry = None
            if entry.get('id') and currents:
                current_entry = currents.find_by_id(entry['id'])

            # if the entry was found, overwrite with the current information,
            # but preserve the credentials
            if isinstance(current_entry, Resource):
                serialized = current_entry.serialize().copy()
                # copy the output and update its values if required
                output = dict(serialized['output']).copy() if serialized.get('output') else {}
                entry_output = dict(entry['output']) if entry.get('output') else {}

                for key, value in entry_output.items():
                    # preserve the current value if the key should be preserved and is empty
                    if key in STATE_OUTPUT_PRESERVED_KEYS and not value:
                        continue

                    # otherwise, update the value
                    output[key] = value

                # update with the current entry values, then overwrite the output
                entry.update({'output': output})

            # the entry should no longer be tainted or touched
            entry.update({
                'reference': entry.get('provision_params', {}).get('reference'),
                'tainted': False,
                'touched': False,
            })

            resources.append(dict(entry))

        return self.__contents.set_path(role, resources)

    @property
    def contents(self):
        """Returns the state file's contents"""
        return self.__contents

    def save(self):
        """Writes out the state file"""
        self.__state_file.contents = self.__contents
        return self.__state_file.write()

    def keys(self):
        """Returns the keys that are stored in the state"""
        return list(self.contents.keys())
