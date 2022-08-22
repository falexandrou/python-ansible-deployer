"""Provides base AWS SES support"""
# -*- coding: utf-8 -*-
import boto3
from botocore.config import Config
from ansible.errors import AnsibleError


class BaseAWSSES:
    """Provides base support for the SES module"""

    DKIM_VERIFICATION_RETRIES = 60
    DKIM_VERIFICATION_SLEEP = 5

    STATE_PRESENT = 'present'
    STATE_ABSENT = 'absent'

    DNS_TTL = 3600
    DNS_ACTION_UPSERT = 'UPSERT'
    DNS_ACTION_REMOVE = 'DELETE'

    def __init__(self, **kwargs):
        route53_config = Config(retries={'max_attempts': 5})
        session = boto3.Session( \
            aws_access_key_id=kwargs.get('aws_access_key'),
            aws_secret_access_key=kwargs.get('aws_secret_key'),
            aws_session_token=kwargs.get('security_token'),
            profile_name=kwargs.get('profile'),
            region_name=kwargs.get('region'))

        self.identity = kwargs.get('identity')
        self.domain = kwargs.get('domain')
        self.zone_id = kwargs.get('hosted_zone_id')
        self.wait = kwargs.get('wait')
        self.region = kwargs.get('region')
        self.ses = session.client('ses')
        self.route53 = session.client('route53', config=route53_config)

    def get_dns_entries(self, items, action=DNS_ACTION_UPSERT):
        """Returns the DNS entries for the module"""
        # pylint: disable=unused-argument,no-self-use
        return []

    def update_dns_records(self, items, action):
        """Modifies the Route53 DNS records"""
        for entry in self.get_dns_entries(items, action):
            response = self.route53.change_resource_record_sets( \
                HostedZoneId=self.zone_id,
                ChangeBatch={'Changes': [entry]})

            if not self.response_success(response):
                raise AnsibleError('Failed to modify DNS record for {}'.format(self.domain))

    @staticmethod
    def response_success(response):
        """Returns whether a response from AWS was successful"""
        return response.get('ResponseMetadata', {}).get('HTTPStatusCode') == 200
