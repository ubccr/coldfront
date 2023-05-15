from copy import deepcopy
from http import HTTPStatus

from django.conf import settings
from django.test import override_settings
from django.urls import reverse

from flags.state import disable_flag
from flags.state import enable_flag
from flags.state import flag_enabled

from coldfront.core.utils.tests.test_base import TestBase


class TestEmailAddresses(TestBase):
    """A class for testing the "Other Email Addresses" section of the
    User Profile."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.client.login(username=self.user.username, password=self.password)

    @staticmethod
    def user_profile_url():
        """Return the URL to the User Profile."""
        return reverse('user-profile')

    def test_section_disabled_if_multiple_addresses_disallowed(self):
        """Test that, if the 'MULTIPLE_EMAIL_ADDRESSES_ALLOWED' feature
        flag is disabled, the section is hidden."""
        flag_name = 'MULTIPLE_EMAIL_ADDRESSES_ALLOWED'
        enable_flag(flag_name)

        response = self.client.get(self.user_profile_url())
        self.assertContains(response, 'Other Email Addresses')
        section_url = reverse('account_email')
        self.assertContains(response, section_url)
        response = self.client.get(section_url)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        flags_copy = deepcopy(settings.FLAGS)
        flags_copy[flag_name] = {'condition': 'boolean', 'value': False}
        with override_settings(FLAGS=flags_copy):
            disable_flag(flag_name)
            self.assertFalse(flag_enabled(flag_name))
            response = self.client.get(self.user_profile_url())
            self.assertNotContains(response, 'Other Email Addresses')
            self.assertNotContains(response, section_url)
            response = self.client.get(section_url)
            self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
