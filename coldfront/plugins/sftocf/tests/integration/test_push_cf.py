# test_integration.py
import unittest

from django.test import TestCase

from coldfront.plugins.sftocf.pipeline import *

class UploadTests(TestCase):
    """Catch issues that may cause database not to upload properly."""
    fixtures = ["coldfront/plugins/sftocf/tests/testdata/fixtures/field_of_science.json",
                "coldfront/plugins/sftocf/tests/testdata/fixtures/all_res_choices.json",
                "coldfront/plugins/sftocf/tests/testdata/fixtures/poisson_fixtures.json",
                "coldfront/plugins/sftocf/tests/testdata/fixtures/project_choices.json"]
    pref = "./coldfront/plugins/sftocf/tests/testdata/"

    def setUp(self):
        self.cfconn = ColdFrontDB()
        suf = "_holysfdb10.json"
        files = ["poisson_lab"]
        self.testfiles = [self.pref + s + suf for s in files]

    def test_push_cf(self):
        self.cfconn.push_cf(self.testfiles, False)


    def test_update_usage(self):
        content = read_json(f"{self.pref}poisson_lab_holysfdb10.json")
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
