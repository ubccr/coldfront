from copy import deepcopy
from http import HTTPStatus
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth import get_user
from django.contrib.auth.models import User
from django.core import mail
from django.test import override_settings
from django.urls import reverse

from allauth.account.models import EmailAddress

from flags.state import disable_flag
from flags.state import enable_flag
from flags.state import flag_enabled

from sesame import settings as sesame_settings

from coldfront.core.user.utils_.link_login_utils import login_token_url
from coldfront.core.user.views_.link_login_views import RequestLoginLinkView
from coldfront.core.utils.tests.test_base import TestBase


class TestLoginLinkViews(TestBase):
    """A class for testing the views for requesting a short-lived login
    link and for authenticating using such links."""

    def setUp(self):
        """Set up test data."""
        enable_flag('BASIC_AUTH_ENABLED')
        enable_flag('LINK_LOGIN_ENABLED')

        super().setUp()

        self.user = User.objects.create(
            email='user@email.com',
            first_name='First',
            last_name='Last',
            username='user',
            is_active=True)
        self.user.set_password(self.password)
        self.user.save()

        self.email_address = EmailAddress.objects.create(
            email=self.user.email,
            user=self.user,
            primary=True,
            verified=True)

        self.assertEqual(len(mail.outbox), 0)

    def _assert_ack_message_sent(self, response):
        """Assert that a message was sent as part of the given response
        noting that an email may have been sent."""
        messages = self.get_message_strings(response)
        self.assertTrue(messages)
        self.assertIn(RequestLoginLinkView.ack_message(), messages)

    def _assert_bad_link_message_sent(self, response):
        """Assert that a message was sent as part of the given response
        noting that the provided login link is invalid or expired."""
        messages = self.get_message_strings(response)
        self.assertTrue(messages)
        self.assertIn('Invalid or expired login link.', messages)

    def _assert_email_confirmed_message_sent(self, response, email):
        """Assert that a message was sent as part of the given response
        noting that the given email address (str) has been confirmed."""
        messages = self.get_message_strings(response)
        self.assertTrue(messages)
        self.assertIn(f'You have confirmed {email}.', messages)

    def _assert_signed_in_message_sent(self, response, username):
        """Assert that a message was sent as part of the given response
        noting that the user with the given username (str) has
        successfully been signed in."""
        messages = self.get_message_strings(response)
        self.assertTrue(messages)
        self.assertIn(f'Successfully signed in as {username}.', messages)

    def _request_login_link(self, email, client=None):
        """Make a POST request to the view to request a login link for
        the given email."""
        if client is None:
            client = self.client
        url = self._view_url()
        data = {'email': email}
        return client.post(url, data, format='json')

    @staticmethod
    def _view_url():
        return reverse('request-login-link')

    def test_expected_flags_enabled(self):
        """Test that, in this test (and by extension every other test in
        the class), the expected authentication-related feature flags
        are enabled."""
        self.assertTrue(flag_enabled('BASIC_AUTH_ENABLED'))
        self.assertTrue(flag_enabled('LINK_LOGIN_ENABLED'))

    def test_views_inaccessible_if_flag_disabled(self):
        """Test that the views are inaccessible if the
        LINK_LOGIN_ENABLED flag is disabled."""
        flag_name = 'LINK_LOGIN_ENABLED'
        enable_flag(flag_name)

        response = self.client.get(self._view_url())
        self.assertEqual(response.status_code, HTTPStatus.OK)

        response = self.client.get(login_token_url(self.user))
        self.assertRedirects(response, reverse('home'))
        client_user = get_user(self.client)
        self.assertTrue(client_user.is_authenticated)
        self._assert_signed_in_message_sent(response, self.user.username)

        self.client.logout()

        flags_copy = deepcopy(settings.FLAGS)
        flags_copy[flag_name] = {'condition': 'boolean', 'value': False}
        with override_settings(FLAGS=flags_copy):
            disable_flag(flag_name)
            self.assertFalse(flag_enabled(flag_name))
            response = self.client.get(self._view_url())
            self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
            response = self.client.get(login_token_url(self.user))
            self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_authenticated_user_redirected(self):
        """Test that an authenticated user attempting to access the view
        is redirected."""
        self.client.login(username=self.user.username, password=self.password)

        response = self.client.get(self._view_url())
        self.assertRedirects(response, reverse('home'))

        response = self._request_login_link(self.user.email)
        self.assertRedirects(response, reverse('home'))

    def test_nonexistent_email_address(self):
        """Test that, when the input email does not correspond to an
        entry in the database:
            - No email is sent.
            - The user receives an acknowledgement.
        """
        self.email_address.delete()

        response = self._request_login_link(self.email_address.email)
        self.assertEqual(len(mail.outbox), 0)
        self._assert_ack_message_sent(response)

    def test_unverified_email_address(self):
        """Test that, when the input email exists but is unverified:
            - A verification email is sent.
            - The user receives an acknowledgement.

        If the user verifies their email and tries again, they should be
        authenticated.
        """
        self.email_address.verified = False
        self.email_address.save()

        response = self._request_login_link(self.email_address.email)
        self._assert_ack_message_sent(response)

        # A verification link should is sent to the address.
        self.assertEqual(len(mail.outbox), 1)
        urls = self.parse_urls_from_str(mail.outbox[0].body)
        self.assertTrue(urls)
        verification_url = urls[0]

        # The user clicks on the link, verifying the address.
        self.client.post(verification_url)
        self.email_address.refresh_from_db()
        self.assertTrue(self.email_address.verified)

        # The user tries again.
        response = self._request_login_link(self.email_address.email)
        self._assert_ack_message_sent(response)

        # A login link is sent to the address.
        self.assertEqual(len(mail.outbox), 2)
        urls = self.parse_urls_from_str(mail.outbox[1].body)
        self.assertTrue(urls)
        login_url = urls[0]

        # The user, who is active, clicks on the link, logging them in.
        self.assertTrue(self.user.is_active)
        response = self.client.get(login_url)
        self.assertRedirects(response, reverse('home'))
        client_user = get_user(self.client)
        self.assertTrue(client_user.is_authenticated)
        self._assert_email_confirmed_message_sent(
            response, self.email_address.email)
        self._assert_signed_in_message_sent(response, self.user.username)

    def test_verified_email_address_user_ineligible(self):
        """Test that when the input email exists and is verified, but
        the user is ineligible to login using a link:
            - An explanatory email is sent.
            - The user receives an acknowledgement.
        """
        self.user.is_staff = False
        self.user.is_superuser = False
        self.user.save()

        user_fields = (
            ('is_staff', True),
            ('is_superuser', True),
            ('is_active', False),
        )
        expected_reason_strs = (
            'portal staff are disallowed',
            'portal staff are disallowed',
            'Inactive users are disallowed',
        )
        for i, user_field in enumerate(user_fields):
            user_field_key, user_field_value = user_field
            setattr(self.user, user_field_key, user_field_value)
            self.user.save()

            response = self._request_login_link(self.email_address.email)
            self._assert_ack_message_sent(response)

            # An email explaining why the user is ineligible is sent to the
            # address.
            self.assertEqual(len(mail.outbox), i + 1)
            body = mail.outbox[i].body
            self.assertIn('ineligible to receive a link', body)
            self.assertIn(expected_reason_strs[i], body)

            setattr(self.user, user_field_key, not user_field_value)
            self.user.save()

        # All causes of ineligibility are removed.
        response = self._request_login_link(self.email_address.email)
        self._assert_ack_message_sent(response)

        # A login link is sent to the address.
        self.assertEqual(len(mail.outbox), len(user_fields) + 1)
        urls = self.parse_urls_from_str(mail.outbox[-1].body)
        self.assertTrue(urls)
        login_url = urls[0]

        # The user clicks on the link, logging them in.
        response = self.client.get(login_url)
        self.assertRedirects(response, reverse('home'))
        client_user = get_user(self.client)
        self.assertTrue(client_user.is_authenticated)
        self._assert_signed_in_message_sent(response, self.user.username)

    def test_verified_email_address_user_eligible(self):
        """Test that when the input email exists and is verified, and
        the user is eligible to login using a link:
            - A login link email is sent.
            - The user receives an acknowledgement.
        """
        response = self._request_login_link(self.email_address.email)
        self._assert_ack_message_sent(response)

        # A login link is sent to the address.
        self.assertEqual(len(mail.outbox), 1)
        urls = self.parse_urls_from_str(mail.outbox[0].body)
        self.assertTrue(urls)
        login_url = urls[0]

        # The user, who is active, clicks on the link, logging them in.
        self.assertTrue(self.user.is_active)
        response = self.client.get(login_url)
        self.assertRedirects(response, reverse('home'))
        client_user = get_user(self.client)
        self.assertTrue(client_user.is_authenticated)
        self._assert_signed_in_message_sent(response, self.user.username)

    def test_login_link_expired(self):
        """Test that, if the login link is expired, authentication
        fails."""
        # Set the max age of a token to 0 seconds.
        with override_settings(SESAME_MAX_AGE=0):
            sesame_settings.load()

        response = self._request_login_link(self.email_address.email)
        self._assert_ack_message_sent(response)

        # A login link is sent to the address.
        self.assertEqual(len(mail.outbox), 1)
        urls = self.parse_urls_from_str(mail.outbox[0].body)
        self.assertTrue(urls)
        login_url = urls[0]

        # The user clicks on the link, but is not authenticated.
        response = self.client.get(login_url)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        client_user = get_user(self.client)
        self.assertFalse(client_user.is_authenticated)
        self._assert_bad_link_message_sent(response)

        # Revert the max age of a token for subsequent tests.
        sesame_settings.load()

    def test_login_link_invalid(self):
        """Test that, if the login link is invalid, authentication
        fails."""
        response = self._request_login_link(self.email_address.email)
        self._assert_ack_message_sent(response)

        # A login link is sent to the address.
        self.assertEqual(len(mail.outbox), 1)
        urls = self.parse_urls_from_str(mail.outbox[0].body)
        self.assertTrue(urls)
        login_url = urls[0]

        # Reverse the token in the URL so that it is invalid.
        parsed_url = urlparse(login_url)
        token = parsed_url.query.split('=')[1]
        modified_token = ''.join(list(reversed(token)))
        modified_url = parsed_url._replace(
            query=f'sesame={modified_token}').geturl()

        # The user clicks on the link, but is not authenticated.
        response = self.client.get(modified_url)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        client_user = get_user(self.client)
        self.assertFalse(client_user.is_authenticated)
        self._assert_bad_link_message_sent(response)

    def test_login_blocked_for_ineligible_user(self):
        """Test that a login link for a user who is ineligible to login
        using a link does not authenticate the user."""
        login_url = login_token_url(self.user)

        self.user.is_staff = False
        self.user.is_superuser = False
        self.user.save()

        user_fields = (
            ('is_staff', True),
            ('is_superuser', True),
            ('is_active', False),
        )
        for i, user_field in enumerate(user_fields):
            user_field_key, user_field_value = user_field
            setattr(self.user, user_field_key, user_field_value)
            self.user.save()

            response = self.client.get(login_url)
            client_user = get_user(self.client)
            self.assertFalse(client_user.is_authenticated)
            self._assert_bad_link_message_sent(response)

            setattr(self.user, user_field_key, not user_field_value)
            self.user.save()

        # All causes of ineligibility are removed. The user clicks on the link,
        # logging them in.
        response = self.client.get(login_url)
        self.assertRedirects(response, reverse('home'))
        client_user = get_user(self.client)
        self.assertTrue(client_user.is_authenticated)
        self._assert_signed_in_message_sent(response, self.user.username)
