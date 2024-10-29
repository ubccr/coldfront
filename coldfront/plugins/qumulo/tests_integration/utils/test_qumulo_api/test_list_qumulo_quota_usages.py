import os

from django.test import TestCase, tag

from unittest import mock

from coldfront.plugins.qumulo.utils.qumulo_api import QumuloAPI
from coldfront.plugins.qumulo.tests_integration.utils.test_qumulo_api.utils import (
    print_all_quotas_with_usage,
)

BLANK = ""


class TestGetAllQuotasWithStatus(TestCase):

    @mock.patch.dict(os.environ, {"QUMULO_RESULT_SET_PAGE_LIMIT": "2000"})
    @tag("integration")
    def test_print_all_quotas_with_usage(self):
        qumulo_api = QumuloAPI()
        print_all_quotas_with_usage(qumulo_api)

    # Currently the page limit was hard coded in the code and is used
    # if it is not specified as an environment variable.
    # It should throw a TypeError Exception.
    # See test_qumulo_result_set_page_limit_should_raise_an_exception_if_not_set.
    @mock.patch.dict(os.environ, {"QUMULO_RESULT_SET_PAGE_LIMIT": ""})
    @tag("integration")
    def test_get_quotas_with_usage_page_limit_not_specified(self):
        qumulo_api = QumuloAPI()
        all_quotas = qumulo_api.get_all_quotas_with_usage()
        paging = all_quotas.get("paging")

        self.assertIsInstance(all_quotas["quotas"], list)
        self.assertIn("quotas", all_quotas)
        self.assertIn("paging", all_quotas)
        self.assertIs(paging.get("next"), BLANK)

    @mock.patch.dict(
        os.environ, {"QUMULO_RESULT_SET_PAGE_LIMIT": "1000000"}
    )  # Arbitrary large number
    @tag("integration")
    def test_get_quotas_with_usage_page_limit_exceeding_qumulo_allocations(self):
        qumulo_api = QumuloAPI()
        all_quotas = qumulo_api.get_all_quotas_with_usage()
        paging = all_quotas.get("paging")

        self.assertIsInstance(all_quotas["quotas"], list)
        self.assertIn("quotas", all_quotas)
        self.assertIn("paging", all_quotas)
        self.assertIs(paging.get("next"), BLANK)

    @mock.patch.dict(os.environ, {"QUMULO_RESULT_SET_PAGE_LIMIT": "2"})
    @tag("integration")
    def test_get_quotas_with_usage_page_limit_specified(self):
        qumulo_api = QumuloAPI()
        all_quotas = qumulo_api.get_all_quotas_with_usage()
        paging = all_quotas.get("paging")

        self.assertIsInstance(all_quotas["quotas"], list)
        self.assertIn("quotas", all_quotas)
        self.assertIn("paging", all_quotas)

        next = paging.get("next")
        page_limit = os.environ.get("QUMULO_RESULT_SET_PAGE_LIMIT")
        limit_param = f"limit={page_limit}"

        self.assertIsNot(next, BLANK)
        self.assertIn(limit_param, next)
