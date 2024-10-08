import re

from django.test import TestCase
from coldfront.plugins.qumulo.utils.eib_billing import (
    get_report_header,
    get_monthly_billing_query_template,
    generate_monthly_billing_report,
)

class TestBillingReport(TestCase):
    def test_header_return_csv(self):
        self.assertTrue(re.search("^Submit Internal Service Delivery,+", get_report_header()))
        
    def test_query_return_sql_statement(self):
        self.assertTrue(re.search("^\s*SELECT\s*", get_monthly_billing_query_template()))

    def test_generate_monthly_billing_report(self):
        self.assertTrue(generate_monthly_billing_report())