from django.test import TestCase, tag
from coldfront.plugins.qumulo.utils.qumulo_api import QumuloAPI
from coldfront.plugins.qumulo.tests_integration.utils.test_qumulo_api.utils import (
    print_all_quotas_with_usage,
)


class TestGetAllQuotasWithStatus(TestCase):
    @tag('integration')
    def test_print_all_quotas_with_usage(self):
        qumulo_api = QumuloAPI()
        print_all_quotas_with_usage(qumulo_api)

    @tag('integration')
    def test_get_all_quotas_with_usage(self):
        qumulo_api = QumuloAPI()
        all_quotas = qumulo_api.get_all_quotas_with_usage()

        self.assertTrue("quotas" in all_quotas)
        self.assertIsInstance(all_quotas["quotas"], list)
