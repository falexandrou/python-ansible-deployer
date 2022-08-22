"""Custom error types"""
# -*- coding: utf-8 -*-

class ProjectTypeNotSupportedError(Exception):
    """Error denoting that the project is not supported"""

class ProjectConfigInvalidError(Exception):
    """Error we're raising when the project config is invalid"""

class ProjectFileMissingError(Exception):
    """Error thrown when the project's config file does not exist"""

class ProjectFileCorruptedError(Exception):
    """Throw when the project's config file is corrupted"""

class ConfigurationFileUnreadableError(Exception):
    """Throw when a configuration file is unreadable"""

class DeploymentFailedError(Exception):
    """Throw when a deployment fails"""

class ServiceNotAvailableError(Exception):
    """Throw when trying to instantiate an invalid service"""

class DependencyNotAvailableError(Exception):
    """Throw when trying to instantiate an invalid dependency"""

class UtilityNotAvailableError(Exception):
    """Throw when trying to instantiate a utility that doesn't exist"""

class NotProvisionableError(Exception):
    """Throw when trying to provision a service or dependency that isn't provisionable"""

class ValidationError(Exception):
    """
    Throw when a model fails to validate
    """
    def __init__(self, errors):
        super().__init__("\n".join(errors.values()))
