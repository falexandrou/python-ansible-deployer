# -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915
import pytest
from . import DepoymentIntegrationTest


def describe_initial_deployment():
    @pytest.fixture
    def site_test(static_site_path, pytestconfig):
        return DepoymentIntegrationTest(
            static_site_path, 'docs.ezploy.eu', pytestconfig=pytestconfig)

    def it_runs_the_deployment(site_test):
        result, operation = site_test.first_deployment(commits_back=1)
        assert site_test.succeeded()
        assert site_test.is_site_up()
        contents = site_test.get_site_contents()
        assert 'An awesome project' in contents

    def it_runs_the_followup_deployment(site_test):
        result, operation = site_test.head_commit_deployment()
        assert site_test.succeeded()
        assert site_test.is_site_up()
        contents = site_test.get_site_contents()
        assert contents
