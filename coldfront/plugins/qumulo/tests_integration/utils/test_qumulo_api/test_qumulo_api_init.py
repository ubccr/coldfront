from django.test import TestCase, tag
from coldfront.plugins.qumulo.utils.qumulo_api import QumuloAPI
import os


class TestQumuloApiInit(TestCase):
    @tag('integration')
    def test_logs_in_without_throwing_error(self):
        try:
            qumulo_api = QumuloAPI()
        except:
            self.fail("Login failed!")
