# -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915
from stackmate.deployables import Deployable
from stackmate.deployables.dependency import Dependency
from stackmate.constants import ROLE_TO_DEPENDS_ON_MAPPING

def describe_deployable():
    #
    # Dependencies
    #
    def it_provides_a_factory_and_a_string_representation(nginx_dependency):
        assert isinstance(nginx_dependency, Deployable)
        assert isinstance(nginx_dependency, Dependency)
        assert str(nginx_dependency) == '<Dependency object id: {}>'.format(id(nginx_dependency))

    def it_provides_the_expected_attributes(nginx_dependency):
        assert nginx_dependency.credentials == {}
        assert nginx_dependency.root_credentials == {}
        assert nginx_dependency.configfiles == []
        assert nginx_dependency.kind == 'nginx'
        assert nginx_dependency.provision_params == {
            'configfiles': [],
            'credentials': {},
            'kind': 'nginx',
            'port': None,
            'root_credentials': {},
            'unique': False,
            'version': '1.18',
            'reference': None,
        }

    def describe_rolename():
        def it_returns_the_utilitys_name_for_when_the_role_is_not_defined(nginx_dependency):
            assert not nginx_dependency.role
            assert nginx_dependency.kind == 'nginx'
            assert nginx_dependency.rolename == nginx_dependency.kind

        def it_returns_the_utilitys_name_for_when_the_role_is_defined(puma_dependency):
            assert puma_dependency.kind == 'puma'
            assert puma_dependency.rolename == 'appservers'

    def describe_depends_on():
        def it_returns_the_roles_that_the_deployable_depends_on(nginx_dependency, puma_dependency):
            assert ROLE_TO_DEPENDS_ON_MAPPING['nginx']
            assert ROLE_TO_DEPENDS_ON_MAPPING['appservers']
            assert nginx_dependency.depends_on == ROLE_TO_DEPENDS_ON_MAPPING['nginx']
            assert puma_dependency.depends_on == ROLE_TO_DEPENDS_ON_MAPPING['appservers']

    def describe_replacement_triggers():
        def it_returns_the_replacement_triggers(nginx_dependency):
            assert hasattr(nginx_dependency, 'replacement_triggers')
            assert sorted(nginx_dependency.replacement_triggers) == sorted([
                'size', 'region', 'provider', 'storage',
            ])
