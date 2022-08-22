# -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915
import pytest
from . import DepoymentIntegrationTest

COMMITS_BACK = 3

def describe_initial_deployment():
    @pytest.fixture
    def application_test(sinatra_app_path, capsys, pytestconfig):
        return DepoymentIntegrationTest(
            sinatra_app_path, 'sinatra.ezploy.eu', capsys=capsys, pytestconfig=pytestconfig)

    def it_runs_the_deployment(application_test):
        result, operation = application_test.first_deployment(commits_back=COMMITS_BACK)
        assert application_test.succeeded()
        assert application_test.is_site_up()
        contents = application_test.get_site_contents()
        assert isinstance(contents, dict)
        assert 'version' in contents
        assert contents['version'] == '1.0'

    def it_runs_the_followup_deployment(application_test):
        result = application_test.head_commit_deployment()
        assert application_test.succeeded()
        assert application_test.is_site_up()
        contents = application_test.get_site_contents()
        assert isinstance(contents, dict)
        assert 'version' in contents
        assert contents['version'] == '2.0'
