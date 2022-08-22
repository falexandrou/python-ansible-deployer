# -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915
import pytest
from . import DepoymentIntegrationTest

def describe_initial_deployment():
    @pytest.fixture
    def application_test(rails_app_path, pytestconfig):
        return DepoymentIntegrationTest(
            rails_app_path, 'rails.ezploy.eu', pytestconfig=pytestconfig)

    def it_runs_the_deployment(application_test):
        result, operation = application_test.head_commit_deployment()
        assert application_test.succeeded()
        assert application_test.is_site_up()
        contents = application_test.get_site_contents()
        assert contents
