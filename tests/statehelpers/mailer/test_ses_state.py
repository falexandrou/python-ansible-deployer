# # -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915,E0401,E0611
import json
import types
from stackmate.ansible.roles.mailer.filter_plugins.helpers \
    import FilterModule, get_stackmate_aws_mailer_state

OUTPUT_FILE = 'stackmate/ansible/roles/mailer/' \
            + 'molecule/aws-ses/' \
            + 'provisioning-output.json'

PROVISION_VARS = None
with open(OUTPUT_FILE) as output:
    PROVISION_VARS = json.load(output)


def test_filter_exported():
    filters = FilterModule().filters()
    assert 'get_stackmate_aws_mailer_state' in filters
    assert isinstance(filters['get_stackmate_aws_mailer_state'], types.FunctionType)


def test_get_stackmate_aws_mailer_state():
    state = get_stackmate_aws_mailer_state(PROVISION_VARS)
    assert isinstance(state, dict)
    assert state['role'] == 'mailer'
    assert 'resources' in state
    assert state['resources']

    for res in state['resources']:
        assert sorted(list(res.keys())) == sorted([
            'created_at', 'group', 'id', 'output',
            'provision_params', 'result', 'side_effects',
        ])

        assert not res['group']
        assert res['id'].startswith('service-mailer-')
        assert isinstance(res['result'], dict)
        assert res['result']['identity'] == res['provision_params']['domain']
        # redis does not provide a configuration endpoint
        assert res['output']['resource_id'] == res['provision_params']['domain']
        assert not res['output']['ip']
        assert not res['output']['nodes']

        assert res['output']['host'] == 'email.eu-central-1.amazonaws.com'
        assert res['output']['port'] == 587
        assert res['output']['username']
        assert res['output']['password']
        assert res['output']['root_username']
        assert res['output']['root_password']
        assert res['output']['key_id'] == res['output']['smtp_username']
        assert res['output']['secret'] == res['output']['root_password']
        assert res['output']['smtp_username']
        assert res['output']['smtp_password']
        assert res['output']['smtp_host'] == 'email-smtp.eu-central-1.amazonaws.com'
        assert 'emails' in res['output']
        assert 'faults' in res['output']
        assert 'deliveries' in res['output']
