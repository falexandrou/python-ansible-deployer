"""Filters for roles that create rds instances"""
# -*- coding: utf-8 -*-
import re
from datetime import datetime


def sns_topic_name(item, topic) -> str:
    """Provides the name for the SNS topic"""
    domain = item.get('provision_params', {}).get('domain')

    if not domain:
        return None

    return 'ses-{domain}-{topic}'.format(
        domain=re.sub(r'([^\w0-9\-])+', '-', domain), topic=topic)


def iam_policy_name(domain: str) -> str:
    """Provides the name to use in the IAM policy"""
    return 'iam-policy-{}'.format(re.sub(r'([^\w0-9\-])+', '-', domain))


def ses_identity_records(recordsets, item):
    """Returns the DNS recordsets related to the SES identity domain"""
    domain = item.get('provision_params', {}).get('domain')
    identity_records = []

    for recordset in recordsets.get('ResourceRecordSets', []):
        name = recordset.get('Name')

        if not name:
            continue

        is_mailer_record = 'mailer.{}.'.format(domain) == name
        is_ses_record = '_amazonses.{}.'.format(domain) == name
        is_dkim_record = name.endswith('_domainkey.{}.'.format(domain))

        if not is_mailer_record and not is_ses_record and not is_dkim_record:
            continue

        values = recordset.get('ResourceRecords', [])
        identity_records.append({
            'name': name,
            'ttl': recordset.get('TTL'),
            'type': recordset.get('Type'),
            'value': values[0].get('Value') if values[0] else None,
        })

    return identity_records


def get_ses_endpoint(region):
    """Get the endpoint for the SES calls"""
    return f'email.{region}.amazonaws.com'


def get_stackmate_aws_mailer_state(variables):
    """
    Returns the state to be used in Stackmate
    """
    resources = []
    rolename = 'mailer'
    provisionables = variables.get('provisions', []) + variables.get('modifications', [])

    for item in provisionables:
        params = item['provision_params']
        res = next(
            (d for d in variables.get('ses_domains', []) if d.get('identity') == params['domain']),
            {}
        )

        [creds] = variables.get('stackmate_generated_credentials', [])
        iam_creds = creds.get('mailer', {}).get('iam', {})
        smtp_creds = creds.get('mailer', {}).get('smtp', {})

        resources.append({
            'id': item['id'],
            'created_at': str(datetime.now()),
            'group': None,
            'provision_params': item['provision_params'],
            'result': res,
            'side_effects': {
                'emails': list(e['results'] for e in res.get('ses_emails', [])),
                'bounces': res.get('sns_bounce_topics'),
                'complaints': res.get('sns_complaints_topics'),
                'deliveries': res.get('sns_deliveries_topics'),
            },
            'output': {
                'resource_id': params['domain'],
                'nodes': [],
                'ip': None,
                'host': get_ses_endpoint(params.get('region', variables.get('region'))),
                'port': smtp_creds.get('port', 587),
                'root_username': iam_creds.get('user_name'),
                'root_password': iam_creds.get('secret_access_key'),
                'username': smtp_creds.get('username'),
                'password': smtp_creds.get('password'),
                'smtp_username': smtp_creds.get('username'),
                'smtp_password': smtp_creds.get('password'),
                'smtp_host': smtp_creds.get('server'),
                'key_id': smtp_creds.get('username'),
                'secret': iam_creds.get('secret_access_key'),
                'emails': params.get('emails', []),
                'faults': params.get('faults', []),
                'deliveries': params.get('deliveries', []),
            }
        })

    return dict(
        role=rolename,
        resources=resources)


def get_ses_username(prefix: str, domain: str):
    """Returns the username to be used as the storage user"""
    return '{prefix}-{suffix}'.format(
        prefix=prefix, suffix=re.sub(r'([^\w]+)', '-', domain))


class FilterModule:
    """Filters used in the mailer role"""
    # pylint: disable=too-few-public-methods,no-self-use
    def filters(self):
        """Filters to be used in the role"""
        return {
            'sns_topic_name': sns_topic_name,
            'iam_policy_name': iam_policy_name,
            'get_ses_username': get_ses_username,
            'ses_identity_records': ses_identity_records,
            'get_stackmate_aws_mailer_state': get_stackmate_aws_mailer_state,
        }
