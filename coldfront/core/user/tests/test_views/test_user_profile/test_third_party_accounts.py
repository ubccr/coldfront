from copy import deepcopy
from http import HTTPStatus

from django.conf import settings
from django.test import override_settings
from django.urls import reverse

from flags.state import disable_flag
from flags.state import enable_flag
from flags.state import flag_enabled

from coldfront.core.utils.tests.test_base import TestBase


class TestThirdPartyAccounts(TestBase):
    """A class for testing the "Third-Party Accounts" section of the
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

    def test_section_disabled_if_flags_disabled(self):
        """Test that, if either the 'MULTIPLE_EMAIL_ADDRESSES_ALLOWED'
        feature flag or the 'SSO_ENABLED' feature flag is disabled, the
        section is hidden."""
        email_flag_name = 'MULTIPLE_EMAIL_ADDRESSES_ALLOWED'
        sso_flag_name = 'SSO_ENABLED'
        enable_flag(email_flag_name)
        enable_flag(sso_flag_name)

        # Both enabled
        response = self.client.get(self.user_profile_url())
        self.assertContains(response, 'Third-Party Accounts')
        section_url = reverse('socialaccount_connections')
        self.assertContains(response, section_url)
        response = self.client.get(section_url)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        disabled_dict = {'condition': 'boolean', 'value': False}
        enabled_dict = {'condition': 'boolean', 'value': True}

        # One enabled, one disabled
        flags_copy = deepcopy(settings.FLAGS)
        flags_copy[email_flag_name] = disabled_dict
        flags_copy[sso_flag_name] = enabled_dict
        with override_settings(FLAGS=flags_copy):
            disable_flag(email_flag_name)
            enable_flag(sso_flag_name)
            self.assertFalse(flag_enabled(email_flag_name))
            self.assertTrue(flag_enabled(sso_flag_name))
            # The section should be hidden.
            response = self.client.get(self.user_profile_url())
            self.assertNotContains(response, 'Third-Party Accounts')
            self.assertNotContains(response, section_url)
            # The underlying view should be inaccessible.
            response = self.client.get(section_url)
            self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

        flags_copy[email_flag_name] = enabled_dict
        flags_copy[sso_flag_name] = disabled_dict
        with override_settings(FLAGS=flags_copy):
            enable_flag(email_flag_name)
            disable_flag(sso_flag_name)
            self.assertTrue(flag_enabled(email_flag_name))
            self.assertFalse(flag_enabled(sso_flag_name))
            # The section should be hidden.
            response = self.client.get(self.user_profile_url())
            self.assertNotContains(response, 'Third-Party Accounts')
            self.assertNotContains(response, section_url)
            # The underlying view should not be accessible.
            response = self.client.get(section_url)
            self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

        # Both disabled
        flags_copy[email_flag_name] = disabled_dict
        flags_copy[sso_flag_name] = disabled_dict
        with override_settings(FLAGS=flags_copy):
            disable_flag(email_flag_name)
            disable_flag(sso_flag_name)
            self.assertFalse(flag_enabled(email_flag_name))
            self.assertFalse(flag_enabled(sso_flag_name))
            # The section should be hidden.
            response = self.client.get(self.user_profile_url())
            self.assertNotContains(response, 'Third-Party Accounts')
            self.assertNotContains(response, section_url)
            # The underlying view should not be accessible.
            response = self.client.get(section_url)
            self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
