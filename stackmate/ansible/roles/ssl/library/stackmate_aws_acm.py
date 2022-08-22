"""ACM module that requests certificates"""
#!/usr/bin/python
# -*- coding: utf-8 -*-
import uuid
import time
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from ansible.module_utils.basic import AnsibleModule
from ansible.errors import AnsibleError
from ansible.module_utils.ec2 import camel_dict_to_snake_dict
from dns import resolver as dnsq

STATE_PRESENT = 'present'
STATE_ABSENT = 'absent'

VALIDATION_METHOD_DNS = 'DNS'
VALIDATION_METHOD_EMAIL = 'EMAIL'

PENDING_STATUS = 'PENDING_VALIDATION'
ISSUED_STATUS = 'ISSUED'

CDN_CERTS_REGION = 'us-east-1'
CERT_MAX_ITEMS = 1000

CERT_REFRESH_TTL = 10
CERT_VALIDATION_RETRIES = 60
CERT_VALIDATION_SLEEP = 5

DNS_TTL = 3600
DNS_ACTION_UPSERT = 'UPSERT'
DNS_ACTION_REMOVE = 'DELETE'

FIELDS = dict(
    certificate_arn=dict(required=False, type="str"),
    aws_access_key=dict(required=False, type="str"),
    aws_secret_key=dict(required=False, type="str", no_log=True),
    security_token=dict(required=False, type="str", no_log=True),
    profile=dict(required=False, type="str"),
    region=dict(required=True, type="str"),
    domain=dict(required=True, type="str"),
    hosted_zone_id=dict(required=True, type="str"),
    alternative_names=dict(required=False, type="list", default=[]),
    cdn_certificate=dict(required=True, type="bool"),
    wait=dict(required=False, type="bool", default=True),
    state=dict(required=False, type="str", default="present", choices=[
        STATE_PRESENT,
        STATE_ABSENT,
    ]),
)

def response_success(response):
    """Returns whether a response from AWS was successful"""
    return response.get('ResponseMetadata', {}).get('HTTPStatusCode') == 200


class StackmateCertificateRequester:
    """Requests and validates an ACM SSL certificate"""
    # pylint: disable=too-many-instance-attributes

    def __init__(self, **kwargs):
        route53_config = Config(retries={'max_attempts': 1})
        session = boto3.Session( \
            aws_access_key_id=kwargs.get('aws_access_key'),
            aws_secret_access_key=kwargs.get('aws_secret_key'),
            aws_session_token=kwargs.get('security_token'),
            profile_name=kwargs.get('profile'),
            region_name=kwargs.get('region'))

        self.domain = kwargs.get('domain')
        self.zone_id = kwargs.get('hosted_zone_id')
        self.alternative_names = kwargs.get('alternative_names') or []
        self.domains = [self.domain]

        if self.alternative_names:
            self.domains += self.alternative_names

        self.acm = session.client('acm')
        self.route53 = session.client('route53', config=route53_config)
        self.idempotency_token = str(uuid.uuid4()).replace('-', '')
        self.certificate_arn = kwargs.get('certificate_arn')
        self._wait_for_validation = kwargs.get('wait')
        self.existing_certificates = self._fetch_existing_certificates()

    def request(self):
        """Requests an SSL certificates via ACM"""
        if not self.domain:
            raise AnsibleError(
                'You have to provide a domain in order to issue the SSL certificate for'
            )

        # Determine validation method
        validation_method = VALIDATION_METHOD_DNS
        if not self.can_use_domain_validation():
            validation_method = VALIDATION_METHOD_EMAIL

        domain_validation_options = [{
            'DomainName': fqdn,
            'ValidationDomain': self.domain,
        } for fqdn in self.domains]

        # Check whether there's an existing certificate
        certificate = self.find_certificate_by_domains()

        if not certificate:
            request_args = dict(
                DomainName=self.domain,
                IdempotencyToken=self.idempotency_token,
                ValidationMethod=validation_method,
                DomainValidationOptions=list(domain_validation_options),
                Tags=[{
                    'Key': 'Name',
                    'Value': 'stackmate-{domain}'.format(domain=self.domain.replace('.', '-')),
                }],
            )

            if self.alternative_names:
                request_args.update(dict(SubjectAlternativeNames=self.alternative_names))

            response = self.acm.request_certificate(**request_args)
            self.certificate_arn = response.get('CertificateArn')

            # We should wait a few seconds before the metadata becomes available
            time.sleep(CERT_REFRESH_TTL)

            # Get the domain validation records
            certificate = self.get_certificate(self.certificate_arn)
        else:
            # certificate was found in the list of the existing ones
            self.certificate_arn = certificate['arn']

        if not certificate['is_verified']:
            validation_records = certificate.get('dns_validation_records', [])

            # Add the validation records to route53
            self.modify_dns_records(validation_records, action=DNS_ACTION_UPSERT)

            # Wait for AWs to validate the certificate
            if self._wait_for_validation:
                return self.wait_for_certificate_validation()

        return certificate

    def terminate(self):
        """Terminate an SSL certificate"""
        certificate = self.find_certificate_by_domains()

        if not certificate:
            raise AnsibleError(
                'Failed to find an SSL certificate with domain {} and alternative_names {}'.format(
                    self.domain, ', '.join(self.alternative_names)))

        self.certificate_arn = certificate['arn']
        validation_records = certificate.get('dns_validation_records', [])

        # Add the validation records to route53
        self.modify_dns_records(validation_records, action=DNS_ACTION_REMOVE)
        response = self.acm.delete_certificate(CertificateArn=self.certificate_arn)

        if not response_success(response):
            raise AnsibleError('Failed to remove SSL certificate {arn}'.format(
                arn=self.certificate_arn))

        return certificate

    def modify_dns_records(self, records: list, action: str):
        """Adds the validation DNS records to Route53"""
        for entry in self.get_dns_entries(records, action):
            try:
                response = self.route53.change_resource_record_sets( \
                    HostedZoneId=self.zone_id,
                    ChangeBatch={'Changes': [entry]})

                if not response_success(response):
                    raise AnsibleError('Failed to modify DNS record for {name}'.format(
                        name=entry.get('ResourceRecordSet', {}).get('Name')))
            except ClientError:
                pass

    def wait_for_certificate_validation(self):
        """Waits for certificate validation"""
        attempts = 0

        certificate = self.get_certificate(self.certificate_arn)
        status = certificate.get('status')

        while attempts <= CERT_VALIDATION_RETRIES and (not status or status == PENDING_STATUS):
            time.sleep(CERT_VALIDATION_SLEEP)
            certificate = self.get_certificate(self.certificate_arn)
            status = certificate.get('status')
            attempts += 1

        return certificate

    def get_certificate(self, arn):
        """Returns the certificate"""
        certificate = self.acm.describe_certificate(CertificateArn=arn).get('Certificate', {})
        return self.transform_output(certificate) if certificate else certificate

    def find_certificate_by_domains(self):
        """Finds a certificate in the list of existing ones based on their domain names"""
        if not self.existing_certificates:
            return None

        for cert in self.existing_certificates:
            expected_alt_names = sorted(self.alternative_names or [])
            alt_names = sorted(
                list([n for n in cert['alternative_names'] if n != self.domain])
            )

            if cert['domain'] == self.domain and alt_names == expected_alt_names:
                return cert

        return None

    def get_dns_entries(self, records: list, action: str = DNS_ACTION_UPSERT) -> list:
        """Returns the DNS entries to be added in Route 53"""
        # pylint: disable=no-self-use
        dns_entries = []
        for record in records:
            res = record.get('resource_record', {})

            entry = {
                'Action': action,
                'ResourceRecordSet': {
                    'Name': res['name'],
                    'Type': res['type'],
                    'ResourceRecords': [{
                        'Value': res['value'],
                    }],
                    'TTL': DNS_TTL,
                }
            }

            if entry not in dns_entries:
                dns_entries.append(entry)

        return dns_entries

    def transform_output(self, certificate):
        """Transforms the certificate output"""
        # pylint: disable=no-self-use
        if not certificate:
            return {}

        certificate = camel_dict_to_snake_dict(certificate)
        is_verified = certificate.get('status') == ISSUED_STATUS

        return dict(
            arn=certificate.get('certificate_arn'),
            domain=certificate.get('domain_name'),
            alternative_names=certificate.get('subject_alternative_names'),
            status=certificate.get('status'),
            is_verified=is_verified,
            algorithm=certificate.get('key_algorithm'),
            created_at=certificate.get('issued_at'),
            dns_validation_records=certificate.get('domain_validation_options', [])
        )

    def can_use_domain_validation(self):
        """Check whether we can use domain validation"""
        answers = []
        domain = self.domain

        while not answers:
            try:
                answers = dnsq.query(domain, 'NS')
            except Exception: # pylint: disable=broad-except
                parts = domain.split('.')[1:]
                if len(parts) < 2:
                    break
                domain = '.'.join(parts)

        nameservers = [rdata.to_text() for rdata in answers]

        return all(['.stackmate.io.' in ns or '.awsdns-' in ns for ns in nameservers])

    def _fetch_existing_certificates(self):
        """Fetches existing certificates"""
        response = self.acm.list_certificates(MaxItems=CERT_MAX_ITEMS)
        arns = []

        for res in response['CertificateSummaryList']:
            if res['DomainName'] == self.domain:
                arns.append(res['CertificateArn'])

        return list([self.get_certificate(arn) for arn in arns])


def main():
    """Execute the module"""
    module = AnsibleModule(argument_spec=FIELDS)
    kwargs = {key: module.params.get(key) for key in FIELDS}
    requester = StackmateCertificateRequester(**kwargs)
    state = module.params.get('state', STATE_PRESENT)

    result = None

    if state == STATE_PRESENT:
        result = requester.request()
    elif state == STATE_ABSENT:
        result = requester.terminate()

    changed = result is not None
    module.exit_json(changed=changed, result=result)

if __name__ == '__main__':
    main()
