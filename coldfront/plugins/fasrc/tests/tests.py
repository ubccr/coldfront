
from django.test import TestCase

from coldfront.plugins.fasrc.utils import (AllTheThingsConn, push_quota_data)

FIXTURES = [
        'coldfront/core/test_helpers/test_data/test_fixtures/resources.json',
        'coldfront/core/test_helpers/test_data/test_fixtures/poisson_fixtures.json',
        'coldfront/core/test_helpers/test_data/test_fixtures/admin_fixtures.json',
        'coldfront/core/test_helpers/test_data/test_fixtures/all_res_choices.json',
        'coldfront/core/test_helpers/test_data/test_fixtures/field_of_science.json',
        'coldfront/core/test_helpers/test_data/test_fixtures/project_choices.json',
        'coldfront/core/test_helpers/test_data/test_fixtures/gordon_fixtures.json',
        ]


class UploadTests(TestCase):
    '''Catch issues that may cause database not to upload properly.'''
    pref = './coldfront/plugins/fasrc/tests/testdata/'
    fixtures = FIXTURES

    def setUp(self):
        self.attconn = AllTheThingsConn()
        self.testfiles = self.pref + 'att_dummy.json'
        self.testpis = self.pref + 'att_pis_dummy.json'
        self.testusers = self.pref + 'att_users_dummy.json'

    def test_push_quota_data(self):
        push_quota_data(self.testfiles)
        # assert AllocationAttribute.
