from django.test import TestCase

from coldfront.core.test_helpers import utils
from coldfront.core.test_helpers.factories import setup_models


UTIL_FIXTURES = [
    "coldfront/core/test_helpers/test_data/test_fixtures/ifx.json",
]

BACKEND = "django.contrib.auth.backends.ModelBackend"

class ResourceViewBaseTest(TestCase):
    """Base test for resource view tests"""
    fixtures = UTIL_FIXTURES

    @classmethod
    def setUpTestData(cls):
        """Test Data setup for all allocation view tests."""
        setup_models(cls)

    def resource_access_tstbase(self, url):
        """Test basic access control for views. For all views:
        - if not logged in, redirect to login page
        - if logged in as admin, can access page
        """
        utils.test_logged_out_redirect_to_login(self, url)
        utils.test_user_can_access(self, self.admin_user, url)  # admin can access

class ResourceListViewTest(ResourceViewBaseTest):
    """Tests for ResourceListView"""

    def setUp(self):
        self.client.force_login(self.admin_user, backend=BACKEND)

