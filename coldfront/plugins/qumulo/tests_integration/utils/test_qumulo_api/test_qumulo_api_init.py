from django.test import TestCase
from coldfront_plugin_qumulo.utils.qumulo_api import QumuloAPI
import os


class TestQumuloApiInit(TestCase):
    def test_logs_in_without_throwing_error(self):
        try:
            qumulo_api = QumuloAPI()
        except:
            self.fail("Login failed!")
