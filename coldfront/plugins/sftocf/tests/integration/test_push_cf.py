# test_integration.py
import unittest
from django.test import TestCase

from coldfront.plugins.sftocf.pipeline import *

class UploadTests(TestCase):
    """Catch issues that may cause database not to upload properly."""

    def setUp(self):
        self.cfconn = ColdFrontDB()

    def test_push_cf(self):
        self.cfconn.push_cf(["./coldfront/plugins/sftocf/tests/testdata/holman_lab_holysfdb01_20211214.json"], False)

    def test_update_usage(self):
        content = read_json("./coldfront/plugins/sftocf/tests/testdata/holman_lab_holysfdb01_20211214.json")
        statdicts = content['contents']
        errors = False
        for statdict in statdicts:
            try:
                server_tier = content['server'] + "/" + content['tier']
                self.cfconn.update_usage(statdict, server_tier)
            except Exception as e:
                logger.debug("EXCEPTION FOR ENTRY: {}".format(e),  exc_info=True)
                print("ERROR:", e)
                errors = True
        assert not errors



if __name__ == '__main__':
    unittest.main()
