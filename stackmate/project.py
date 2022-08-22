"""Provides support for given project types"""
# -*- coding: utf-8 -*-
from __future__ import annotations
import os
from stackmate.base import Model, ModelAttribute
from stackmate.constants import ENV_PUBLIC_KEY, ENV_PRIVATE_KEY, DEPLOYMENT_USER, \
                                PROJECT_TYPES, PROJECT_FLAVORS, PROJECT_FLAVOR_INSTANCES
from stackmate.configurations import ProjectConfiguration, ProjectVault
from stackmate.exceptions import ValidationError
from stackmate.helpers import flatten
from stackmate.deployables.service import Service
from stackmate.deployables.dependency import Dependency
from stackmate.deployables.utility import Utility
from stackmate.configurations import STACKMATE_CONFIGURATION
from stackmate.types import DeployableList


class Project(Model):
    """Base Class for projects"""
    # pylint: disable=too-many-instance-attributes
    _framework = ModelAttribute(required=True, datatype=str, choices=PROJECT_TYPES)
    _repository = ModelAttribute(required=True, datatype=str)
    _flavor = ModelAttribute(required=True, datatype=str, \
        choices=PROJECT_FLAVORS, default=PROJECT_FLAVOR_INSTANCES)

    # environment specific attributes
    _user = ModelAttribute(required=False, datatype=str, default=DEPLOYMENT_USER)
    _documentroot = ModelAttribute(required=False, datatype=str)
    _ssl = ModelAttribute(required=False, datatype=dict)
    _provider = ModelAttribute(required=True, datatype=str, \
        choices=STACKMATE_CONFIGURATION.get_path('providers'))
    _region = ModelAttribute(required=True, datatype=str)
    _providers = ModelAttribute(required=True, datatype=dict)
    _branch = ModelAttribute(required=True, datatype=str)
    _domain = ModelAttribute(required=True, datatype=str)
    _pipeline = ModelAttribute(required=False, datatype=dict, default={})
    _environment = ModelAttribute(required=False, datatype=dict, default={}, serializable=False)
    _configfiles = ModelAttribute(required=False, datatype=list, default=[], serializable=False)
    _notifications = ModelAttribute(required=False, datatype=list, default=[])
    _services = ModelAttribute(required=True, datatype=list, serializable=False)
    _statics = ModelAttribute(required=False, datatype=list, serializable=False)

    @staticmethod
    def load(rootpath, stage):
        """Loads a project"""
        return Project( \
            configuration=ProjectConfiguration(rootpath=rootpath, stage=stage),
            stage=stage,
            vault=ProjectVault(rootpath=rootpath))

    def __init__(self, configuration, **kwargs):
        super().__init__(**kwargs)
        self.configuration = configuration
        self.rootpath = self.configuration.rootpath
        self.attributes = self.configuration.contents # assign the model's attributes
        self._stage = kwargs.get('stage')
        self._vault = kwargs.get('vault')
        self._deployables = None
        self._deployables_per_role = {}

    @property
    def stage(self):
        """Returns the currently selected stage"""
        return self._stage

    @property
    def ssh_keys(self):
        """Returns the public & private SSH keys as files and text"""
        public_file = os.environ.get(ENV_PUBLIC_KEY)
        private_file = os.environ.get(ENV_PRIVATE_KEY)

        if not public_file or not private_file:
            raise ValidationError( \
                'Please export the {pub} and {priv} environment variables'.format(
                    pub=ENV_PUBLIC_KEY,
                    priv=ENV_PRIVATE_KEY))

        public_key = None
        private_key = None

        if public_file:
            with open(public_file) as public:
                public_key = public.read().strip()

        if private_file:
            with open(private_file) as private:
                private_key = private.read().strip()

        return {
            'public_key_filename': public_file,
            'private_key_filename': private_file,
            'public_key': public_key,
            'private_key': private_key,
        }

    @property
    def vault(self):
        """Returns the credentials vault"""
        return self._vault

    @property
    def path(self):
        """Return the path to the project's configuration"""
        return self.configuration.path

    def service_configs(self) -> dict:
        """Service configurations found in the project"""
        return self.configuration.contents.get('services', {})

    def provider_credentials(self, provider):
        """Get a provider's credentials"""
        return {
            'username': self._vault.contents.get_path('provider_%s_username' % provider),
            'password': self._vault.contents.get_path('provider_%s_password' % provider),
        }

    def _collect_deployables(self) -> DeployableList:
        """Collects deployables for the project"""
        # start parsing the services
        services = Service.collect(project=self)
        dependencies = Dependency.collect(project=self, services=services)
        utilities = flatten([
            Utility.collect(u, project=self, services=services, dependencies=dependencies)
            for u in Utility.available(self.provider)
        ])

        return services + dependencies + utilities

    @property
    def deployables(self):
        """Returns the full list of deployables"""
        if self._deployables is None:
            self._deployables = self._collect_deployables()

        return self._deployables

    @property
    def deployables_per_role(self):
        """Returns an index of the project's deployables indexed by role"""
        if self._deployables_per_role:
            return self._deployables_per_role

        for dep in self.deployables:
            if dep.rolename not in self._deployables_per_role:
                self._deployables_per_role[dep.rolename] = []

            self._deployables_per_role[dep.rolename].append(dep)

        return self._deployables_per_role
