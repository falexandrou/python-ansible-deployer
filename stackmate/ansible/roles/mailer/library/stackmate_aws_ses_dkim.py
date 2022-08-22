"""AWS module that provides missing functionality for the SES service"""
#!/usr/bin/python
# -*- coding: utf-8 -*-
import time
from ansible.module_utils.basic import AnsibleModule
from ansible.errors import AnsibleError
from ansible.module_utils.base import BaseAWSSES # pylint: disable=import-error, no-name-in-module

FIELDS = dict(
    identity=dict(required=True, type="str"),
    domain=dict(required=True, type="str"),
    aws_access_key=dict(required=False, type="str"),
    aws_secret_key=dict(required=False, type="str", no_log=True),
    security_token=dict(required=False, type="str", no_log=True),
    profile=dict(required=False, type="str"),
    region=dict(required=True, type="str"),
    hosted_zone_id=dict(required=True, type="str"),
    wait=dict(required=False, type="bool", default=True),
    state=dict(required=False, type="str", default="present", choices=[
        BaseAWSSES.STATE_PRESENT,
        BaseAWSSES.STATE_ABSENT,
    ]),
)


class StackmateSESDKIMEnabler(BaseAWSSES):
    """Handles AWS SES DKIM validation and status"""
    def enable(self):
        """Enables and verifies the DKIM setting"""
        response = self.ses.verify_domain_dkim(Domain=self.domain)

        if not response or not response.get('DkimTokens', []):
            raise AnsibleError('Failed to fetch DKIM validation tokens')

        self.update_dns_records(response.get('DkimTokens', []), action=self.DNS_ACTION_UPSERT)

        response = self.ses.set_identity_dkim_enabled(
            DkimEnabled=True,
            Identity=self.identity,
        )

        if not self.response_success(response):
            raise AnsibleError(
                'Failed to enable DKIM for identity {}'.format(self.identity)
            )

        output = {
            'identity': self.identity,
            'dkim_verified': self.get_is_dkim_verified(),
        }

        if not self.wait:
            return output

        is_verified = self.wait_for_dkim_validation()

        if not is_verified:
            raise AnsibleError('Failed to verify DKIM for identity {}'.format(self.identity))

        output.update({'is_verified': is_verified})
        return output

    def disable(self):
        """Disables DKIM for an SES identity"""
        response = self.ses.verify_domain_dkim(Domain=self.domain)
        if not response or not response.get('DkimTokens', []):
            raise AnsibleError('Failed to fetch DKIM validation tokens')

        self.update_dns_records(response.get('DkimTokens', []), action=self.DNS_ACTION_REMOVE)

        response = self.ses.set_identity_dkim_enabled(
            DkimEnabled=False,
            Identity=self.identity,
        )

        if not self.response_success(response):
            raise AnsibleError(
                'Failed to disable DKIM for identity {}'.format(self.identity)
            )

        return response

    def get_is_dkim_verified(self):
        """Returns whether DKIM is verified for the given identity"""
        attrs = self.ses.get_identity_dkim_attributes(Identities=[self.identity])

        if not attrs or not attrs.get('DkimAttributes', {}).get(self.identity):
            return False

        entry = attrs.get('DkimAttributes', {}).get(self.identity)
        return entry.get('DkimVerificationStatus') == 'Success'

    def wait_for_dkim_validation(self):
        """Waits for certificate validation"""
        attempts = 0

        is_verified = self.get_is_dkim_verified()

        while attempts <= self.DKIM_VERIFICATION_RETRIES and not is_verified:
            time.sleep(self.DKIM_VERIFICATION_SLEEP)
            is_verified = self.get_is_dkim_verified()
            attempts += 1

        return is_verified

    def get_dns_entries(self, items: list, action: str = BaseAWSSES.DNS_ACTION_UPSERT) -> list:
        """Returns the DNS entries to be added in Route 53"""
        # pylint: disable=no-self-use
        dns_entries = []
        for token in items:
            # Format for the records
            # Name : token ._domainkey.*example.com*
            # Type : CNAME
            # Value : token .dkim.amazonses.com
            entry = {
                'Action': action,
                'ResourceRecordSet': {
                    'Name': '{}._domainkey.{}'.format(token, self.domain),
                    'Type': 'CNAME',
                    'ResourceRecords': [{
                        'Value': '{}.dkim.amazonses.com'.format(token),
                    }],
                    'TTL': self.DNS_TTL,
                }
            }

            if entry not in dns_entries:
                dns_entries.append(entry)

        return dns_entries

def main():
    """Execute the module"""
    module = AnsibleModule(argument_spec=FIELDS)
    kwargs = {key: module.params.get(key) for key in FIELDS}
    requester = StackmateSESDKIMEnabler(**kwargs)
    state = module.params.get('state', StackmateSESDKIMEnabler.STATE_PRESENT)

    result = None

    if state == StackmateSESDKIMEnabler.STATE_PRESENT:
        result = requester.enable()
    elif state == StackmateSESDKIMEnabler.STATE_ABSENT:
        result = requester.disable()

    changed = result is not None
    module.exit_json(changed=changed, result=result)

if __name__ == '__main__':
    main()
