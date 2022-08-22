"""AWS module that provides missing functionality for the SES service"""
#!/usr/bin/python
# -*- coding: utf-8 -*-
import boto3
from ansible.module_utils.basic import AnsibleModule
from ansible.errors import AnsibleError

FIELDS = dict(
    iam_user=dict(required=True, type="str"),
    region=dict(required=True, type="str"),
    profile=dict(required=False, type="str"),
    aws_access_key=dict(required=True, type="str"),
    aws_secret_key=dict(required=True, type="str", no_log=True),
    security_token=dict(required=False, type="str", no_log=True),
)


class StackmateRemoveAccessKeys:
    """Describes an IAM user"""
    # pylint: disable=too-few-public-methods
    def __init__(self, **kwargs):
        session = boto3.Session( \
            aws_access_key_id=kwargs.get('aws_access_key'),
            aws_secret_access_key=kwargs.get('aws_secret_key'),
            aws_session_token=kwargs.get('security_token'),
            profile_name=kwargs.get('profile'),
            region_name=kwargs.get('region'))

        self.iam_user = kwargs.get('iam_user')
        self.iam = session.client('iam')

    def remove_credentials(self):
        """Describes an IAM user"""
        if not self.iam_user:
            raise AnsibleError('Name not provided')

        try:
            response = self.iam.list_access_keys(UserName=self.iam_user)
        except self.iam.exceptions.NoSuchEntityException:
            return 0

        access_key_ids = [
            e['AccessKeyId'] for e in response.get('AccessKeyMetadata', []) if e.get('AccessKeyId')
        ]

        removed = 0
        for access_key_id in access_key_ids:
            self.iam.delete_access_key(
                UserName=self.iam_user,
                AccessKeyId=access_key_id)
            removed += 1

        return removed


def main():
    """Execute the module"""
    module = AnsibleModule(argument_spec=FIELDS)
    kwargs = {key: module.params.get(key) for key in FIELDS}

    result = StackmateRemoveAccessKeys(**kwargs).remove_credentials()
    changed = result > 0

    module.exit_json(changed=changed, result=result)

if __name__ == '__main__':
    main()
