from coldfront.core.utils.tests.test_base import TestBase
from copy import deepcopy
from django.conf import settings
from django.test import override_settings
from django.urls import reverse
from flags.state import disable_flag
from flags.state import enable_flag


class TestRenewPIAllocationLandingView(TestBase):
    """A class for testing the landing view for requesting to renew a
    PI's allocation."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)

    @staticmethod
    def view_url():
        """Return the URL for the landing view."""
        return reverse('renew-pi-allocation-landing')

    def test_next_allowance_year_alert_appears_conditionally(self):
        """Test that an alert, which notes that renewals for the next
        allowance year are available, only appears when a particular
        feature flag is enabled."""
        flag_name = 'ALLOCATION_RENEWAL_FOR_NEXT_PERIOD_REQUESTABLE'

        alert_text = 'The allowance year for FCAs is ending soon'

        enable_flag(flag_name)
        url = self.view_url()
        response = self.client.get(url)
        self.assertContains(response, alert_text)

        disable_flag(flag_name)
        # The flag must also be disabled in settings.
        flags_copy = deepcopy(settings.FLAGS)
        flags_copy.pop(flag_name)
        with override_settings(FLAGS=flags_copy):
            url = self.view_url()
            response = self.client.get(url)
            self.assertNotContains(response, alert_text)
