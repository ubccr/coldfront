import string
import filecmp

from django.test import TestCase
from django.contrib.auth import get_user_model
from ifxuser.models import IfxUser, Organization
from coldfront.plugins.fasrc.utils import AllTheThingsConn, log_missing

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
        # assert AllocationAttribute.

    def test_log_missing(self):
        vowels = ['a','e','i','o','u']
        datapath = "./coldfront/plugins/fasrc/tests/testdata/"
        modelname = "project"
        model_attr_list = [f"{v}_lab" for v in vowels]
        search_list = [f"{c}_lab" for c in list(string.ascii_lowercase)]
        log_missing(modelname, model_attr_list, search_list, fpath_pref=datapath)
        assert filecmp.cmp(f'{datapath}missing_projects.csv', f'{datapath}missing_projects_compare.csv') == True


if __name__ == '__main__':
    unittest.main()
