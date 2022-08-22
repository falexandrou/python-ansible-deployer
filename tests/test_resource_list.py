# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915
import pytest
from stackmate.resources import Resource, ResourceList
from stackmate.deployables.service import Service

def describe_provision_resources():
    @pytest.fixture
    def resource_list(state):
        return state.get_resources('databases')

    @pytest.fixture
    def psql_service(project):
        cfgs = project.configuration.contents.get_path('services')
        rdb = next((c for c in cfgs if c.get('type') == 'mysql'), None)
        assert rdb
        # make it a
        psqldb = dict(rdb).copy()
        psqldb.update({
            'type': 'postgresql',
            'version': '10.10',
            'name': 'postgresql-database',
            'provider': 'aws',
            'region': 'eu-central-1',
        })

        return Service.factory(**psqldb)

    def it_initializes_without_resources():
        subject = ResourceList()
        assert isinstance(subject, ResourceList)
        assert subject.all == []

    def it_acts_as_a_list_of_resources(resource_list):
        assert all(isinstance(res, Resource) for res in resource_list.all)

    def it_finds_the_resources_that_refer_to_the_deployable(resource_list, mysql_service):
        resources = resource_list.find(mysql_service)
        assert len(resources) == 1

        assert resources[0].id
        assert resources[0].provision_params['kind']

        assert resources[0].id == mysql_service.deployable_id
        assert resources[0].provision_params['kind'] == mysql_service.kind

    def it_finds_a_resource_by_id(resource_list):
        existing_id = resource_list.all[0].id
        found = resource_list.find_by_id(existing_id)
        assert isinstance(found, Resource)
        assert found.id == existing_id

        missing_id = 'something-that-doesnt-exist-in-the-whole-universe'
        existing_ids = [res.id for res in resource_list.all]
        assert missing_id not in existing_ids
        found = resource_list.find_by_id(missing_id)
        assert not found

    def it_terminates_resources_for_a_deployable(resource_list, mysql_service):
        terminations = resource_list.terminate(mysql_service)
        assert len(terminations) == 1

    def it_provisions_resources_for_a_deployable(psql_service, resource_list):
        # not found in the resource list
        assert not resource_list.find(psql_service)
        resource_list.provision(psql_service)

        resources = resource_list.find(psql_service)
        assert len(resources) == 1

        assert resources[0].id == psql_service.deployable_id
        assert resources[0].provision_params['kind'] == psql_service.kind

    def it_modifies_the_resources_for_a_deployable(resource_list, mysql_service):
        resources = resource_list.find(mysql_service)
        assert len(resources) == 1

        modifications = resource_list.modify(mysql_service)
        assert len(modifications) == 1

    def it_returns_whether_the_deployable_exists_in_the_list(resource_list, mysql_service, \
        python_dependency):
        assert resource_list.exists(mysql_service)
        assert not resource_list.exists(python_dependency)

    def it_returns_whether_the_list_has_changes(resource_list, psql_service):
        assert not resource_list.has_changes()
        resource_list.provision(psql_service)
        assert resource_list.has_changes()

    def it_returns_the_unchanged_resources(resource_list, mysql_service):
        cnt = len(resource_list.unchanged())
        allcnt = len(resource_list)

        resource_list.modify(mysql_service)

        assert len(resource_list) == allcnt
        assert len(resource_list.unchanged()) == (cnt - 1)

    def it_serializes_the_list(resource_list, mysql_service):
        cnt = len(resource_list.unchanged())

        resource_list.modify(mysql_service)
        serialized = resource_list.serialize()

        assert set(serialized.keys()) == set([
            'provisions', 'modifications', 'terminations', 'unchanged', 'has_changes',
        ])

        assert serialized['provisions'] == []
        assert len(serialized['modifications']) == 1
        assert serialized['terminations'] == []
        assert len(serialized['unchanged']) == cnt - 1
        assert serialized['has_changes']

    def it_terminates_unused_resources(resource_list, mysql_service):
        cnt = len(resource_list.all)
        assert resource_list.exists(mysql_service)

        resource_list.terminate_unused_resources([mysql_service])
        assert len(resource_list.all) == cnt
        serialized = resource_list.serialize()

        assert serialized['provisions'] == []
        assert serialized['modifications'] == []
        assert len(serialized['terminations']) == cnt - 1
        assert len(serialized['unchanged']) == 1
        assert serialized['has_changes']

        assert serialized['unchanged'][0]['id'] == mysql_service.deployable_id
        assert mysql_service.deployable_id not in [t['id'] for t in serialized['terminations']]

    def it_does_not_provision_a_deployable_twice(mysql_service):
        resource_list = ResourceList()
        # we're adding the exact same resource, so adding it multiple times
        # would only include the deployable once in the resource list
        resource_list.provision(mysql_service)
        resource_list.provision(mysql_service)
        resource_list.provision(mysql_service)

        changes = resource_list.serialize()
        assert changes['provisions']
        assert len(changes['provisions']) == 1

    def it_does_not_modify_a_resource_twice(resource_list, mysql_service):
        # we're modifying the exact same resource so calling the modify function multiple times
        # should only include the deployable once in the list
        resource_list.modify(mysql_service)
        resource_list.modify(mysql_service)
        resource_list.modify(mysql_service)
        resource_list.modify(mysql_service)

        changes = resource_list.serialize()
        assert changes['modifications']
        assert len(changes['modifications']) == 1

    def it_provisions_deployables_with_multiple_nodes():
        pass

    def it_does_not_terminate_a_resource_twice(resource_list, mysql_service):
        # we're terminating the exact same resource so calling the termintate function
        # multiple times should only include the deployable once in the list
        resource_list.terminate(mysql_service)
        resource_list.terminate(mysql_service)
        resource_list.terminate(mysql_service)

        changes = resource_list.serialize()
        assert changes['terminations']
        assert len(changes['terminations']) == 1
