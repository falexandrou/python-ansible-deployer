# -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915
import os
import pytest
from stackmate.constants import ENV_STACKMATE_OPERATION_ID
from . import DepoymentIntegrationTest

COMMITS_BACK = 4

def describe_initial_deployment():
    @pytest.fixture
    def application_test(django_app_path, pytestconfig):
        os.environ[ENV_STACKMATE_OPERATION_ID] = '2000'

        return DepoymentIntegrationTest(
            django_app_path, 'django.ezploy.eu', pytestconfig=pytestconfig)

    def it_runs_the_deployment(application_test):
        result, operation = application_test.first_deployment(commits_back=COMMITS_BACK)
        assert application_test.succeeded()
        # assert application_test.is_site_up()
        # contents = application_test.get_site_contents()
        # assert 'Incident report' in contents


    # def it_runs_the_followup_deployment(application_test):
    #     result = application_test.head_commit_deployment()
    #     assert application_test.succeeded()
    #     # assert application_test.is_site_up()
    #     # contents = application_test.get_site_contents()
    #     # assert 'System status report' in contents
