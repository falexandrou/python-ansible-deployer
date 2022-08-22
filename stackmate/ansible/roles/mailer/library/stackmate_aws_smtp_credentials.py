"""AWS module that provides missing functionality for the SES service"""
#!/usr/bin/python
# -*- coding: utf-8 -*-
import hmac
import hashlib
import base64
from ansible.module_utils.basic import AnsibleModule
from ansible.errors import AnsibleError

FIELDS = dict(
    region=dict(required=True, type="str"),
    access_key=dict(required=True, type="str"),
    secret_key=dict(required=True, type="str", no_log=True),
)

SMTP_PORT = 587
DATE = "11111111"
SERVICE = "ses"
MESSAGE = "SendRawEmail"
TERMINAL = "aws4_request"
VERSION = 0x04


def sign(key, msg):
    """Signs a hash with a given key and message"""
    return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()


class StackmateSMTPCredentials:
    """Generates SMTP credentials for a given IAM user"""
    def __init__(self, **kwargs):
        # these values refer to the IAM user access key, not the overall account
        self.access_key = kwargs.get('access_key')
        self.secret_key = kwargs.get('secret_key')
        self.region = kwargs.get('region')

    def get_smtp_server(self):
        """Generates the address to use as an SMTP server"""
        return 'email-smtp.{region}.amazonaws.com'.format(region=self.region)

    def generate(self):
        """Generates the credentials for when connecting to AWS SMTP servers"""
        if not self.access_key:
            raise AnsibleError('The access key has not been provided')

        return {
            'server': self.get_smtp_server(),
            'username': self.access_key,
            'password': self.get_smtp_password(),
            'port': SMTP_PORT,
        }

    def get_smtp_password(self):
        """Calculates the AWS secret access key for the user"""
        # @see https://docs.aws.amazon.com/ses/latest/DeveloperGuide/smtp-credentials.html
        if not self.secret_key:
            raise AnsibleError('The secret key has not been provided')

        signature = sign(("AWS4" + self.secret_key).encode('utf-8'), DATE)
        signature = sign(signature, self.region)
        signature = sign(signature, SERVICE)
        signature = sign(signature, TERMINAL)
        signature = sign(signature, MESSAGE)
        signature_with_version = bytes([VERSION]) + signature
        password = base64.b64encode(signature_with_version)
        return password.decode('utf-8')

def main():
    """Execute the module"""
    module = AnsibleModule(argument_spec=FIELDS)
    kwargs = {key: module.params.get(key) for key in FIELDS}

    result = StackmateSMTPCredentials(**kwargs).generate()
    changed = result is not None

    module.exit_json(changed=changed, result=result)

if __name__ == '__main__':
    main()
