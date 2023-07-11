from django.test import TestCase

from coldfront.plugins.fasrc.utils import AllTheThingsConn, push_quota_data
from coldfront.core.test_helpers.factories import (
    setup_models,
    UserFactory,
    ProjectFactory,
    ResourceFactory,
    AllocationFactory,
    AAttributeTypeFactory,
    AllocationAttributeTypeFactory,
)


UTIL_FIXTURES = [
        "coldfront/core/test_helpers/test_data/test_fixtures/ifx.json",
]


class UploadTests(TestCase):
    """Catch issues that may cause database not to upload properly."""
    pref = './coldfront/plugins/fasrc/tests/testdata/'
    fixtures = UTIL_FIXTURES

    @classmethod
    def setUpTestData(cls):
        """Test Data setup for all allocation view tests.
        """
        setup_models(cls)
        aalice = UserFactory(username='aalice', is_staff=False, is_superuser=False)
        gordon_lab = ProjectFactory(pi=aalice, title="gordon_lab")
        gordon_alloc = AllocationFactory(project=gordon_lab)
        gordon_alloc.resources.add(ResourceFactory(name='holylfs10/tier1', id=1))
        AllocationAttributeTypeFactory(
            name='RequiresPayment', attribute_type=AAttributeTypeFactory(name='Boolean')
        )
        AllocationAttributeTypeFactory(
            name='Subdirectory', attribute_type=AAttributeTypeFactory(name='Text')
        )

    def setUp(self):
        self.attconn = AllTheThingsConn()
        self.testfiles = self.pref + 'att_dummy.json'
        self.testpis = self.pref + 'att_pis_dummy.json'
        self.testusers = self.pref + 'att_users_dummy.json'

    def test_push_quota_data(self):
        """Ensure that push runs successfully"""
        push_quota_data(self.testfiles)
        # assert AllocationAttribute.
