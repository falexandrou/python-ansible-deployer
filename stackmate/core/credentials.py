"""Credentials for the project's services"""
# -*- coding: utf-8 -*-
from __future__ import annotations
from stackmate.base import Model, ModelAttribute
from stackmate.configurations import ProjectVault

class Credentials(Model):
    """Represents the project's services credentials"""
    _username = ModelAttribute(required=True, datatype=str)
    _password = ModelAttribute(required=True, datatype=str)

    @staticmethod
    def load(service: str, vault: ProjectVault, root: bool = False) -> Credentials:
        """Load the credentials from the vault"""
        username_key = '{srv}_username'.format(srv=service)
        password_key = '{srv}_password'.format(srv=service)

        if root:
            username_key = 'root_' + username_key
            password_key = 'root_' + password_key

        username = vault.contents.get_path(username_key)
        password = vault.contents.get_path(password_key)

        return Credentials(username=username, password=password)

    def serialize(self):
        return {
            'username': self.username,
            'password': self.password,
        }
