# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915,R0914
import pytest
from stackmate.provisioner import Provisioner
from stackmate.resources import ResourceList

def describe_provisioner():
    @pytest.fixture
    def db_resource_list(state):
        return state.get_resources('databases')

    @pytest.fixture
    def nginx_resource_list(state):
        return state.get_resources('nginx')

    @pytest.fixture
    def python_resource_list(state):
        return state.get_resources('python')

    @pytest.fixture
    def cdn_resource_list(state):
        return state.get_resources('cdn')

    @pytest.fixture
    def ssl_resource_list(state):
        return state.get_resources('ssl')

    @pytest.fixture
    def mailer_resource_list(state):
        return state.get_resources('mailer')

    @pytest.fixture
    def ssl_dependency(project):
        return next((d for d in project.deployables if d.rolename == 'ssl'), None)

    @pytest.fixture
    def mock_resource(application_service_multinode):
        [mock_resource] = application_service_multinode.as_node_resources()[:1]
        mock_resource.output = {
            'resource_id': None,
            'ip': None,
            'host': None,
            'port': None,
            'nodes': [{
                'name': '{}-1'.format(application_service_multinode.name),
                'resource_id': 'instance-1',
                'ip': '123.123.123.123',
                'host': 'host1.ec2.aws.amazon.com',
            }, {
                'name': '{}-2'.format(application_service_multinode.name),
                'resource_id': 'instance-2',
                'ip': '123.123.123.124',
                'host': 'host2.ec2.aws.amazon.com',
            }, {
                'name': '{}-3'.format(application_service_multinode.name),
                'resource_id': 'instance-3',
                'ip': '123.123.123.125',
                'host': 'host3.ec2.aws.amazon.com',
            }],
        }

        return mock_resource

    def it_determines_changes_for_a_resource_list_that_contains_mysql( \
        db_resource_list, mysql_service):
        assert db_resource_list.exists(mysql_service)
        changes = Provisioner.changes([mysql_service], db_resource_list, set(), set())
        cnt = len(db_resource_list.all)

        assert not changes['provisions']
        assert not changes['modifications']
        assert len(changes['terminations']) == cnt - 1
        assert len(changes['unchanged']) == 1
        assert changes['has_changes']

        assert changes['unchanged'][0]['id'] == mysql_service.deployable_id
        assert mysql_service.deployable_id not in [t['id'] for t in changes['terminations']]

    def it_upgrades_nginx(nginx_resource_list, nginx_dependency):
        assert nginx_resource_list.exists(nginx_dependency)
        changes = Provisioner.changes([nginx_dependency], nginx_resource_list, set(), set())

        assert not changes['provisions']
        assert len(changes['modifications']) == 1
        assert changes['modifications'][0]['id'] == nginx_dependency.deployable_id
        assert not changes['terminations']
        assert not changes['unchanged']
        assert changes['has_changes']

    def it_does_not_return_any_changes_when_the_provision_params_match(nginx_resource_list, \
            nginx_dependency):
        assert nginx_resource_list.exists(nginx_dependency)
        [nginx_resource] = nginx_resource_list.all[:1]
        nginx_resource.provision_params['version'] = nginx_dependency.version
        changes = Provisioner.changes([nginx_dependency], nginx_resource_list, set(), set())
        assert not changes
        assert changes == {}

    def it_returns_modifications_when_the_role_it_depends_upon_changed(nginx_resource_list, \
            nginx_dependency):
        assert nginx_resource_list.exists(nginx_dependency)
        [nginx_resource] = nginx_resource_list.all[:1]

        # make sure no changes are there when no updated_roles is present
        nginx_resource.provision_params['version'] = nginx_dependency.version

        changes = Provisioner.changes([nginx_dependency], nginx_resource_list, set(), set())
        assert changes == {}

        changes = Provisioner.changes(
            [nginx_dependency], nginx_resource_list, set(nginx_dependency.depends_on), set())
        assert not changes['provisions']
        assert len(changes['modifications']) == 1
        assert changes['modifications'][0]['id'] == nginx_dependency.deployable_id
        assert not changes['terminations']
        assert not changes['unchanged']
        assert changes['has_changes']

    def it_retuns_modifications_when_role_is_provisioned_and_dependencies_change(\
            ssl_resource_list, ssl_dependency):
        assert not ssl_resource_list.exists(ssl_dependency)

        changes = Provisioner.changes(
            [ssl_dependency], ssl_resource_list, set(['prerequisites']), set())
        assert changes
        assert 'provisions' in changes
        assert len(changes['provisions']) == 1

    def it_provisions_python(python_resource_list, python_dependency):
        assert not python_resource_list.exists(python_dependency)
        assert not python_resource_list.all
        changes = Provisioner.changes([python_dependency], python_resource_list, set(), set())
        assert len(changes['provisions']) == 1
        assert changes['provisions'][0]['id'] == python_dependency.deployable_id
        assert not changes['modifications']
        assert not changes['terminations']
        assert not changes['unchanged']
        assert changes['has_changes']

    def it_does_not_replace_a_service_when_their_core_attributes_change( \
            db_resource_list, mysql_modified):
        assert db_resource_list.exists(mysql_modified)
        changes = Provisioner.changes([mysql_modified], db_resource_list, set(), set())
        assert not changes['provisions']
        assert changes['modifications']
        assert changes['modifications'][0]['id'] == mysql_modified.deployable_id
        assert len(changes['terminations']) >= 1
        assert not mysql_modified.deployable_id in [t['id'] for t in changes['terminations']]
        assert changes['has_changes']

    def it_picks_the_entries_requested(db_resource_list, mysql_modified):
        # Only pick the provisions at first
        assert db_resource_list.exists(mysql_modified)
        changes = Provisioner.changes([mysql_modified], db_resource_list, set(), {'provisions'})
        assert changes == {}

        # only pick the terminations now
        changes = Provisioner.changes([mysql_modified], db_resource_list, set(), {'terminations'})
        assert not changes['provisions']
        assert not changes['modifications']
        assert len(changes['terminations']) >= 1

    def it_provisions_a_service_with_nodes_when_no_entry_in_the_resource_list(\
            application_service_multinode):
        assert hasattr(application_service_multinode, 'nodes')
        assert application_service_multinode.nodes > 1
        resource_list = ResourceList()
        changes = Provisioner.changes([application_service_multinode], resource_list, set(), set())
        expected_keys = ['provisions', 'modifications', 'terminations', 'unchanged', 'has_changes']
        assert all(k in changes for k in expected_keys)
        assert changes['has_changes']
        assert len(changes['provisions']) == application_service_multinode.nodes
        assert not changes['modifications']
        assert not changes['terminations']
        assert not changes['unchanged']
        provision_names = {p['provision_params']['name'] for p in changes['provisions']}
        expected_names = set([
            'application-server-1', 'application-server-2', 'application-server-3',
        ])
        assert provision_names == expected_names

    def it_leaves_resources_for_a_servie_with_nodes_intact_when_no_changes_have_taken_place(\
            application_service_multinode, mock_resource):
        resource_list = ResourceList(resources=[mock_resource])
        changes = Provisioner.changes([application_service_multinode], resource_list, set(), set())
        assert isinstance(changes, dict)
        assert not changes

    def it_provisions_a_service_with_nodes_when_increasing_the_nodes_count_and_state_has_nodes(\
            application_service_multinode, mock_resource):
        additional = 2
        initial = application_service_multinode.nodes
        application_service_multinode.nodes += additional
        resource_list = ResourceList(resources=[mock_resource])
        changes = Provisioner.changes([application_service_multinode], resource_list, set(), set())
        assert isinstance(changes, dict)
        assert len(changes['provisions']) == additional
        assert changes['has_changes']
        assert not changes['terminations']
        assert not changes['modifications']
        assert len(changes['unchanged']) == initial

    def it_provisions_a_service_with_nodes_when_decreasing_the_nodes_count_and_state_has_nodes( \
            application_service_multinode, mock_resource):
        reduction = 2
        initial = application_service_multinode.nodes
        application_service_multinode.nodes -= reduction
        resource_list = ResourceList(resources=[mock_resource])
        changes = Provisioner.changes([application_service_multinode], resource_list, set(), set())
        assert isinstance(changes, dict)
        assert not changes['provisions']
        assert changes['has_changes']
        assert len(changes['terminations']) == reduction
        assert not changes['modifications']
        assert len(changes['unchanged']) == initial - reduction

    def it_marks_cdn_services_for_replacement_when_the_origins_have_changed(cdn_service, \
            cdn_resource_list):
        assert len(cdn_resource_list) == 1
        origins = cdn_service.origins
        for origin in origins:
            origin['aliases'].append('new.ezploy.eu')
        cdn_service.origins = origins
        changes = Provisioner.changes([cdn_service], cdn_resource_list, set(), set())
        assert isinstance(changes, dict)
        assert len(changes['provisions']) == 1
        prov = changes['provisions'][0]
        assert 'new.ezploy.eu' in prov['provision_params']['origins'][0]['aliases']
        assert len(changes['terminations']) == 1
        assert not changes['modifications']
        assert not changes['unchanged']

    def it_modifies_touched_resources(db_resource_list, mysql_service):
        changes = Provisioner.changes([mysql_service], db_resource_list, set(), set())
        assert not changes['modifications']
        assert changes['unchanged']

        entry = changes['unchanged'][0]
        resource = db_resource_list.find(mysql_service)[0]

        # make sure we're updating the correct resource
        assert entry['id'] == resource.id
        resource.touch()

        # touch the resource that is in the unchanged list
        changes = Provisioner.changes([mysql_service], db_resource_list, set(), set())
        assert changes['modifications']
        assert len(changes['modifications']) == 1
        assert changes['modifications'][0]['id'] == entry['id']
        assert not changes['unchanged']

    def it_checks_whether_we_should_regenerate_credentials(mailer_service, mailer_resource_list):
        assert len(mailer_resource_list) == 1
        assert not Provisioner.should_regenerate_credentials(mailer_service, mailer_resource_list)

    def it_requires_to_regenerate_credentials_if_missing(mailer_service, mailer_resource_list):
        assert len(mailer_resource_list) == 1
        mailer_resource_list.all[0].output.update({'username': None})
        assert Provisioner.should_regenerate_credentials(mailer_service, mailer_resource_list)

    def it_does_not_add_multiple_modifications_when_a_resource_is_touched(\
            db_resource_list, mysql_modified):
        # first verify that we're only modifying
        assert db_resource_list.exists(mysql_modified)
        db_resource_list.touch(mysql_modified)

        changes = Provisioner.changes(
            [mysql_modified], db_resource_list, set(), {'provisions', 'modifications'})

        assert not changes['provisions']
        assert changes['modifications']
        assert len(changes['modifications']) == 1
        assert not changes['terminations']
        assert changes['has_changes']
