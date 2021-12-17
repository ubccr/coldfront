# test_integration.py
import unittest
from django.test import TestCase

from coldfront.plugins.sftocf.pipeline import *

class UploadTests(TestCase):
    """Catch issues that may cause database not to upload properly."""
    pref = "./coldfront/plugins/sftocf/tests/testdata/"

    def setUp(self):
        self.cfconn = ColdFrontDB()
        suf = "_test.json"
        files = ["holman_lab_holysfdb01", "hoekstra_lab_holysfdb02", "ham_lab_holysfdb02", "lemos_lab_holysfdb02", "zhang_lab_holysfdb01"]
        self.testfiles = [self.pref + s + suf for s in files]

    def test_push_cf(self):
        self.cfconn.push_cf(self.testfiles, False)

    def test_update_usage(self):
        content = read_json(f"{self.pref}holman_lab_holysfdb01_test.json")
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
