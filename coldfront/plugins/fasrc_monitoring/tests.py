
from django.test import TestCase, Client
from django.contrib.auth import get_user_model

from coldfront.config.env import ENV
from coldfront.core.test_helpers.factories import setup_models

UTIL_FIXTURES = [
        "coldfront/core/test_helpers/test_data/test_fixtures/ifx.json",
]


class MonitorViewTest(TestCase):

    fixtures = UTIL_FIXTURES

    @classmethod
    def setUpTestData(cls):
        """Test Data setup for all allocation view tests.
        """
        setup_models(cls)

    def setUp(self):
        self.admin_user = get_user_model().objects.get(username='gvanrossum')
        self.project_pi = get_user_model().objects.get(username='sdpoisson')
        self.client = Client()

    def test_monitor_access(self):
        """Confirm that only admins can access the page
        """
        # check that login is required
        # utils.test_logged_out_redirect_to_login(self, '/monitor')
        response = self.client.get('/monitor')
        self.assertEqual(response.status_code, 404)
        # existing project pi cannot access
        self.client.force_login(self.project_pi,
                    backend='django.contrib.auth.backends.ModelBackend')
        response = self.client.get('/monitor')
        self.assertEqual(response.status_code, 404)

    def test_monitor_admin_access(self):
        # admin can access
        self.client.force_login(self.admin_user,
                backend='django.contrib.auth.backends.ModelBackend')
        response = self.client.get('/monitor')
        if ENV.bool('PLUGIN_FASRC_MONITORING', default=False):
            self.assertEqual(response.status_code, 200)
        else:
            self.assertEqual(response.status_code, 404)
