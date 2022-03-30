from django.test import TestCase
from django.contrib.auth import get_user_model
from ifxuser.models import IfxUser, Organization
from coldfront.plugins.fasrc.utils import AllTheThingsConn

class UploadTests(TestCase):
    """Catch issues that may cause database not to upload properly."""
    fixtures = ["coldfront/plugins/fasrc/tests/testdata/fixtures/field_of_science.json",
                "coldfront/plugins/fasrc/tests/testdata/fixtures/all_res_choices.json",
                "coldfront/plugins/fasrc/tests/testdata/fixtures/poisson_fixtures.json",
                "coldfront/plugins/fasrc/tests/testdata/fixtures/gordon_fixtures.json",
                "coldfront/plugins/fasrc/tests/testdata/fixtures/dummy_fixtures.json",
                "coldfront/plugins/fasrc/tests/testdata/fixtures/project_choices.json"]
    pref = "./coldfront/plugins/fasrc/tests/testdata/"

    def setUp(self):
        self.attconn = AllTheThingsConn()
        self.testfiles = self.pref + "att_dummy.json"

    def test_push_quota_data(self):
        self.attconn.push_quota_data(self.testfiles)
        print("Done!")


if __name__ == '__main__':
    unittest.main()
