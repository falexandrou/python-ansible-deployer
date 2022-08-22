"""AWS module that provides missing functionality for the SES service"""
#!/usr/bin/python
# -*- coding: utf-8 -*-
from ansible.module_utils.basic import AnsibleModule
from ansible.errors import AnsibleError
from ansible.module_utils.base import BaseAWSSES # pylint: disable=import-error, no-name-in-module

FIELDS = dict(
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


class StackmateSESMailFromEnabler(BaseAWSSES):
    """Handles AWS SES DKIM validation and status"""
    def enable(self):
        """Enables and verifies the DKIM setting"""
        response = self.ses.set_identity_mail_from_domain(
            BehaviorOnMXFailure='UseDefaultValue',
            Identity=self.domain,
            MailFromDomain=self.get_outbound_subdomain(),
        )

        if not self.response_success(response):
            raise AnsibleError(
                'Failed to enable MAIL FROM for domain {}'.format(self.domain)
            )

        return self.update_dns_records(self.get_records(), action=BaseAWSSES.DNS_ACTION_UPSERT)

    def disable(self):
        """Disables DKIM for an SES identity"""
        self.ses.set_identity_mail_from_domain(
            BehaviorOnMXFailure='UseDefaultValue',
            Identity=self.domain,
            MailFromDomain=None,
        )

        return self.update_dns_records(self.get_records(), action=BaseAWSSES.DNS_ACTION_REMOVE)

    def get_outbound_subdomain(self):
        """Returns the outbound subdomain to set"""
        return 'mailer.{}'.format(self.domain)

    def get_records(self):
        """Returns the DNS records to set in Route53"""
        outbound_subdomain = self.get_outbound_subdomain()

        return [
            {
                'record': outbound_subdomain,
                'value': '10 feedback-smtp.{}.amazonses.com'.format(self.region),
                'type': 'MX',
            },
            {
                'record': outbound_subdomain,
                'value': '"v=spf1 include:amazonses.com ~all"',
                'type': 'TXT',
            },
        ]

    def get_dns_entries(self, items: list, action: str = BaseAWSSES.DNS_ACTION_UPSERT) -> list:
        """Returns the DNS entries to be added in Route 53"""
        # pylint: disable=no-self-use
        dns_entries = []
        for item in items:
            # Format for the records
            # Name : token ._domainkey.*example.com*
            # Type : CNAME
            # Value : token .dkim.amazonses.com
            entry = {
                'Action': action,
                'ResourceRecordSet': {
                    'Name': item.get('record'),
                    'Type': item.get('type'),
                    'ResourceRecords': [{'Value': item.get('value')}],
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
    requester = StackmateSESMailFromEnabler(**kwargs)
    state = module.params.get('state', StackmateSESMailFromEnabler.STATE_PRESENT)

    result = None

    if state == StackmateSESMailFromEnabler.STATE_PRESENT:
        result = requester.enable()
    elif state == StackmateSESMailFromEnabler.STATE_ABSENT:
        result = requester.disable()

    changed = result is not None
    module.exit_json(changed=changed, result=result)

if __name__ == '__main__':
    main()
