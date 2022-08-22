"""Configurations regarding the project"""
# -*- coding: utf-8 -*-

import os
from abc import ABC
from stackmate.base import AttributeDict
from stackmate.helpers import read_yaml, write_yaml
from stackmate.exceptions import ProjectFileMissingError, ProjectFileCorruptedError, \
    ConfigurationFileUnreadableError

# Config files
PROJECT_CONFIG_FILE = 'config.yml'
OPERATIONS_CONFIG_FILE = 'operations.yml'
STATE_CONFIG_FILE = 'state.yml'
MAIN_CONFIG_FILE = 'stackmate.yml'
VAULT_FILE = 'vault.yml'

class ConfigurationFile(ABC):
    """Abstract class representing configuration files"""
    def __init__(self, rootpath=None, filename=None):
        self.rootpath = rootpath if rootpath else os.getcwd()
        self._filename = filename
        self._contents = {}

    @property
    def filename(self):
        """Return the config file's name"""
        return self._filename

    @property
    def exists(self):
        """Returns if the file exists"""
        return os.path.isfile(self.path)

    @property
    def directory_exists(self):
        """Returns whether the directory exists"""
        return os.path.isdir(self.rootpath)

    @property
    def path(self):
        """Returns the full path for the file"""
        return os.path.join(self.rootpath, self.filename)

    @property
    def contents(self):
        """Returns the file's contents"""
        if not self._contents:
            self._contents = self.read()
        return self._contents

    @contents.setter
    def contents(self, contents):
        """Sets the file's contents"""
        self._contents = self._parse_contents(contents)

    def read(self):
        """Read the configuration file"""
        return self._parse_contents(read_yaml(self.path))

    def write(self):
        """Writes the configuration file"""
        return write_yaml(self.path, self._contents)

    def _parse_contents(self, contents):
        # pylint: disable=no-self-use
        """Parses the file's contents"""
        return AttributeDict(contents or {})


class ReadOnlyConfigurationFile(ConfigurationFile):
    """Makes a configuration file read-only"""
    def write(self):
        raise Exception('This file is read-only')


class BranchedConfiguration(ConfigurationFile):
    # pylint: disable=too-few-public-methods
    """Config file where there are branches of configurations"""

    ROOT_ATTRIBUTES = []

    def __init__(self, rootpath=None, filename=None):
        super().__init__(rootpath, filename)
        self._branch = None
        self._full_contents = None

    def set_branch(self, branch):
        """Sets the configuration branch to read from / write to"""
        self._branch = branch

    def get_branch(self):
        """Returns the contents' branch"""
        return self._full_contents.get(self._branch) or {}

    def get_root_attributes(self, contents):
        """Returns the root attributes from the contents specified"""
        return {k:v for k, v in contents.items() if k in self.__class__.ROOT_ATTRIBUTES} or {}

    @property
    def contents(self):
        """Sets the file's contents"""
        return super().contents

    @contents.setter
    def contents(self, contents: dict):
        # Reverse operation: form the full contents from the branched contents specified
        content_keys = contents.keys()
        mutable = dict(contents).copy()

        full_contents = {
            k:mutable.pop(k) for k in content_keys if k in self.__class__.ROOT_ATTRIBUTES
        }

        # now update the rest of the contents as the branch
        full_contents.update({self._branch: mutable})

        self._full_contents = full_contents
        self._contents = self._parse_contents(self._full_contents)

    @property
    def full_contents(self):
        """Returns the full contents of the file"""
        return self._full_contents

    def _parse_contents(self, contents):
        """Gets the contents of a configration file branched out on a specific branch"""
        self._full_contents = contents
        branch = self.get_branch() or {}
        root = self.get_root_attributes(contents) or {}

        return AttributeDict(dict(**root, **branch))

    def write(self):
        """Writes the configuration file"""
        return write_yaml(self.path, self._full_contents)


class CreatableConfiguration(ConfigurationFile):
    """Represents configuration files that we don't mind if they initially don't exist"""

    def read(self):
        """Load the project's configuration"""
        contents = None

        try:
            contents = super().read()
        except ConfigurationFileUnreadableError:
            contents = AttributeDict({})
        except FileNotFoundError:
            contents = AttributeDict({})

        return contents


class StackmateConfiguration(ReadOnlyConfigurationFile):
    """Represents the global application's configuration"""

    def __init__(self):
        super().__init__(
            rootpath=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config'),
            filename=MAIN_CONFIG_FILE)


class OperationsConfiguration(ReadOnlyConfigurationFile):
    """Represents the operations to be executed in playbooks"""

    def __init__(self):
        super().__init__(
            rootpath=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config'),
            filename=OPERATIONS_CONFIG_FILE)


class ProjectConfiguration(ReadOnlyConfigurationFile, BranchedConfiguration):
    """Represents a project's configuration"""
    ROOT_ATTRIBUTES = [
        'framework', 'repository', 'notifications',
        'provider', 'region', 'providers', 'documentroot',
    ]

    def __init__(self, rootpath, stage):
        super().__init__(rootpath=rootpath, filename=PROJECT_CONFIG_FILE)
        self.set_branch(stage)

    def read(self):
        """Load the project's configuration"""
        if not self.exists:
            raise ProjectFileMissingError('File %s does not exist' % self.path)

        contents = None

        try:
            contents = super().read()
        except ConfigurationFileUnreadableError:
            contents = None

        if not contents:
            raise ProjectFileCorruptedError

        return contents


class ProjectState(BranchedConfiguration, CreatableConfiguration):
    """
    The Project's state file
    """
    ROOT_ATTRIBUTES = ['version']

    def __init__(self, rootpath, stage):
        super().__init__(rootpath=rootpath, filename=STATE_CONFIG_FILE)
        self.set_branch(stage)


class ProjectVault(CreatableConfiguration):
    """Represents the project vault where the credentials are stored"""
    def __init__(self, rootpath):
        super().__init__(rootpath=rootpath, filename=VAULT_FILE)


# export the default configuration
STACKMATE_CONFIGURATION = StackmateConfiguration().contents
