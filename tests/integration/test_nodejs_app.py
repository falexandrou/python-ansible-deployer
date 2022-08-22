# -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915
import pytest
from . import DepoymentIntegrationTest

COMMITS_BACK = 1

def describe_initial_deployment():
    @pytest.fixture
    def application_test(nodejs_app_path, pytestconfig):
        return DepoymentIntegrationTest(
            nodejs_app_path, 'nodejs.ezploy.eu', pytestconfig=pytestconfig)

    def it_runs_the_deployment(application_test):
        result, operation = application_test.first_deployment(commits_back=COMMITS_BACK)
        assert application_test.succeeded()
        assert application_test.is_site_up()
        contents = application_test.get_site_contents()
        assert 'Today is a good day' in contents


    def it_runs_the_followup_deployment(application_test):
        result = application_test.head_commit_deployment()
        assert application_test.succeeded()
        assert application_test.is_site_up()
        contents = application_test.get_site_contents(url='/status')
        assert 'All systems reporting at 100%' in contents
