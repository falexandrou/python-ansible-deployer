# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915
import pytest
from stackmate.resources import Resource

def describe_resource():
    @pytest.fixture
    def sample_resource(state):
        dblist = state.get_resources('databases').all

        return next(
            (r for r in dblist if r.provision_params['kind'] == 'mysql'),
            None
        )

    @pytest.fixture
    def resource_list(state):
        return state.get_resources('databases').all

    def it_determines_whether_the_resource_refers_to_a_deployable(resource_list, mysql_service):
        # verify our fixture is OK:
        ids = [res.id for res in resource_list]
        assert mysql_service.deployable_id in ids

        relevant = next(
            (res for res in resource_list if res.id == mysql_service.deployable_id), None
        )

        irrelevant = next(
            (res for res in resource_list if res.id != mysql_service.deployable_id), None
        )

        assert relevant.refers_to(mysql_service)
        assert not irrelevant.refers_to(mysql_service)

    def it_initializes_with_the_provision_params_attribute_only(project_config):
        srv_config = project_config.contents.services[0]
        resource = Resource(group=srv_config.type, provision_params=srv_config)
        assert isinstance(resource, Resource)
        assert 'nodes' not in resource.provision_params.keys()
        # the provision params doesn't have any kind or nodes
        diff = set(srv_config) - set(resource.provision_params)
        assert all([attr in Resource.PROHIBITED_PARAMS for attr in diff])

    def it_initializes_with_all_the_attributes_present(sample_resource):
        resource = Resource(**sample_resource.serialize())
        assert isinstance(resource, Resource)
        assert resource.created_at == sample_resource.created_at
        assert frozenset(dict(resource.output)) == frozenset(dict(sample_resource.output))
        assert resource.tainted == sample_resource.tainted
        assert hasattr(resource, 'reference')

    def it_gets_tainted(sample_resource):
        resource_attrs = dict(**sample_resource.serialize())
        resource_attrs.update({'tainted': False})

        resource = Resource(**resource_attrs)
        assert resource.tainted is False

        resource.taint()
        assert resource.tainted is True

    def it_gets_touched(sample_resource):
        resource_attrs = dict(**sample_resource.serialize())
        resource_attrs.update({'touched': False})

        resource = Resource(**resource_attrs)
        assert resource.touched is False

        resource.touch()
        assert resource.touched is True

    def it_returns_two_resources_with_the_same_params_as_identical(sample_resource):
        other_resource = Resource(**sample_resource.serialize())
        assert sample_resource.diff_params(other_resource) == {}

    def it_returns_the_diff_between_two_resources(sample_resource):
        params = sample_resource.provision_params.copy()
        changes = {'version': '5.8', 'size': 'db.t2.large', 'storage': 500}
        params.update(changes)

        another_resource = Resource(group='application', provision_params=params)
        diff = another_resource.diff_params(sample_resource)
        assert set(diff.keys()) == set(['version', 'size', 'storage'])
        assert diff == changes
