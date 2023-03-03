from coldfront.core.utils.fasrc import read_json

from django.test import TestCase
from django.contrib.auth import get_user_model
from coldfront.plugins.fasrc.utils import AllTheThingsConn, add_new_projects

class UploadTests(TestCase):
    '''Catch issues that may cause database not to upload properly.'''
    fixtures = ['coldfront/plugins/fasrc/tests/testdata/fixtures/field_of_science.json',
                'coldfront/plugins/fasrc/tests/testdata/fixtures/all_res_choices.json',
                'coldfront/plugins/fasrc/tests/testdata/fixtures/poisson_fixtures.json',
                'coldfront/plugins/fasrc/tests/testdata/fixtures/gordon_fixtures.json',
                'coldfront/plugins/fasrc/tests/testdata/fixtures/dummy_fixtures.json',
                'coldfront/plugins/fasrc/tests/testdata/fixtures/project_choices.json']
    pref = './coldfront/plugins/fasrc/tests/testdata/'

    def setUp(self):
        self.attconn = AllTheThingsConn()
        self.testfiles = self.pref + 'att_dummy.json'
        self.testpis = self.pref + 'att_pis_dummy.json'
        self.testusers = self.pref + 'att_users_dummy.json'

    def test_push_quota_data(self):
        self.attconn.push_quota_data(self.testfiles)
        # assert AllocationAttribute.

    def test_add_new_projects(self):
        '''to test:
        - all projects with pis are added
        - all projects with active pis not yet added to ifxuser are recorded for later addition
        - project pis that aren't listed in adusers are still added as projectusers
        - all project users are correctly added or recorded
        '''
        pi_data = read_json(self.testpis)
        aduser_data = read_json(self.testusers)
        added_projs = add_new_projects(pi_data, aduser_data)
        self.assertEqual(len(added_projs) == 0)
        isaac = get_user_model().objects.create(
                password="",
                full_name="Isaac Newton",
                username="inewton",
                first_name="Isaac",
                last_name="Newton",
                )
        added_projs = add_new_projects(pi_data, aduser_data)
        self.assertEqual(len(added_projs) == 1)
