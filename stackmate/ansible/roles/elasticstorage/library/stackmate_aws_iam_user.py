"""AWS module that provides missing functionality for the SES service"""
#!/usr/bin/python
# -*- coding: utf-8 -*-
import boto3
from ansible.module_utils.basic import AnsibleModule
from ansible.errors import AnsibleError

FIELDS = dict(
    name=dict(required=True, type="str"),
    region=dict(required=True, type="str"),
    profile=dict(required=False, type="str"),
    aws_access_key=dict(required=True, type="str"),
    aws_secret_key=dict(required=True, type="str", no_log=True),
    security_token=dict(required=False, type="str", no_log=True),
)


class StackmateIAMUser:
    """Describes an IAM user"""
    # pylint: disable=too-few-public-methods
    def __init__(self, **kwargs):
        session = boto3.Session( \
            aws_access_key_id=kwargs.get('aws_access_key'),
            aws_secret_access_key=kwargs.get('aws_secret_key'),
            aws_session_token=kwargs.get('security_token'),
            profile_name=kwargs.get('profile'),
            region_name=kwargs.get('region'))

        self.name = kwargs.get('name')
        self.iam = session.client('iam')

    def get_user(self):
        """Describes an IAM user"""
        if not self.name:
            raise AnsibleError('Name not provided')

        return self.iam.get_user(UserName=self.name).get('User')

def main():
    """Execute the module"""
    module = AnsibleModule(argument_spec=FIELDS)
    kwargs = {key: module.params.get(key) for key in FIELDS}

    result = StackmateIAMUser(**kwargs).get_user()
    changed = result is not None

    module.exit_json(changed=changed, result=result)

if __name__ == '__main__':
    main()
