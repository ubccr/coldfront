from copy import deepcopy
from http import HTTPStatus
from urllib.parse import parse_qs
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth import get_user
from django.contrib.auth.models import User
from django.core import mail
from django.core.validators import validate_email
from django.test import override_settings
from django.urls import reverse
from django.utils.http import urlencode

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
from allauth.socialaccount.providers.base import AuthProcess
from allauth.tests import MockedResponse
from allauth.tests import mocked_response
from flags.state import disable_flag
from flags.state import enable_flag
from flags.state import flag_enabled

from coldfront.core.utils.tests.test_base import TestBase

import json


class TestCILogonAccountAdapter(TestBase):

    def setUp(self):
        """Set up test data."""
        super().setUp()
        enable_flag('SSO_ENABLED')
        self._cilogon_provider = 'cilogon'
        self._assert_authenticated(negate=True)

    def _assert_authenticated(self, negate=False):
        """Assert that the current client User is or is not
        authenticated."""
        client_user = get_user(self.client)
        if not negate:
            self.assertTrue(client_user.is_authenticated)
        else:
            self.assertFalse(client_user.is_authenticated)

    def _assert_successful_cilogin_response(self, response,
                                            process=AuthProcess.LOGIN):
        """Assert that the given response, resulting from the given
        CILogon process, redirects to the expected URL and has the
        expected messages. Provide the username """
        if process == AuthProcess.LOGIN:
            expected_message = (
                f'Successfully signed in as '
                f'{response.wsgi_request.user.username}.')
            redirect_url = reverse('home')
        elif process == AuthProcess.CONNECT:
            expected_message = 'The social account has been connected.'
            redirect_url = reverse('socialaccount_connections')
        else:
            raise ValueError('Unexpected auth process.')
        self.assertRedirects(response, redirect_url)
        messages = self.get_message_strings(response)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0], expected_message)

    @staticmethod
    def _cilogon_user_data(email=None, eppn=None, given_name=None,
                           family_name=None, idp_name=None, sub=None):
        """Return a dict simulating user data returned by the CILogon
        provider, with the given fields. If a field is not given, a
        default is used."""
        if email is None:
            email = 'user@email.com'
        if eppn is None:
            eppn = 'user@email.com'
        if given_name is None:
            given_name = 'First'
        if family_name is None:
            family_name = 'Last'
        if idp_name is None:
            idp_name = 'Test University'
        if sub is None:
            sub = 'http://cilogon.org/serverA/users/1234567'
        return {
            'email': email,
            'eppn': eppn,
            'given_name': given_name,
            'family_name': family_name,
            'idp_name': idp_name,
            'sub': sub,
        }

    @staticmethod
    def _cilogon_login_url(process=AuthProcess.LOGIN):
        """Return the URL for authenticating via CILogon. Optionally
        override the allauth AuthProcess."""
        return f'{reverse("cilogon_login")}?{urlencode(dict(process=process))}'

    def _simulate_cilogon_login(self, cilogon_user_data,
                                process=AuthProcess.LOGIN):
        """Simulate logging in with CILogon with a user having
        attributes in the given dict.

        Optionally override the allauth AuthProcess.

        Adapted from allauth.socialaccount.tests.OAuth2TestsMixin.login.
        """
        response = self.client.post(self._cilogon_login_url(process=process))
        p = urlparse(response['location'])
        q = parse_qs(p.query)

        headers = {'content-type': 'application/json'}
        mock_cilogon_user_data_response = MockedResponse(
            HTTPStatus.OK, json.dumps(cilogon_user_data), headers=headers)
        login_response_json_str = {'uid': 'uid', 'access_token': 'access_token'}
        mock_login_response = MockedResponse(
            HTTPStatus.OK, json.dumps(login_response_json_str), headers=headers)

        with mocked_response(
                mock_login_response, mock_cilogon_user_data_response):
            complete_url = reverse('cilogon_callback')
            response = self.client.get(
                complete_url, {'code': 'test', 'state': q['state'][0]},
                follow=True)
        return response

    def test_connect_process_disallowed_if_flag_disabled(self):
        """Test that, when the MULTIPLE_EMAIL_ADDRESSES_ALLOWED flag is
        disabled, Users are not allowed to connect additional
        SocialAccounts to an existing account."""
        cilogon_user_data = self._cilogon_user_data()

        # Sign up
        response = self._simulate_cilogon_login(cilogon_user_data)
        self._assert_successful_cilogin_response(response)

        num_users = User.objects.count()
        num_social_accounts = SocialAccount.objects.count()
        num_email_addresses = EmailAddress.objects.count()

        new_cilogon_user_data = self._cilogon_user_data(
            email='newuser@email.com',
            eppn='newuser@email.com',
            idp_name='New Test University',
            sub='http://cilogon.org/serverA/users/7654321')

        flag_name = 'MULTIPLE_EMAIL_ADDRESSES_ALLOWED'

        # Disabled
        flags_copy = deepcopy(settings.FLAGS)
        flags_copy[flag_name] = {'condition': 'boolean', 'value': False}
        with override_settings(FLAGS=flags_copy):
            disable_flag(flag_name)
            self.assertFalse(flag_enabled(flag_name))
            response = self._simulate_cilogon_login(
                new_cilogon_user_data, process=AuthProcess.CONNECT)
            self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

            expected_error_message = (
                'You may not connect more than one third-party account to '
                'your portal account.')
            self.assertEqual(
                response.context['message'], expected_error_message)

            self.assertEqual(SocialAccount.objects.count(), num_social_accounts)

        # Enabled
        flags_copy[flag_name]['value'] = True
        with override_settings(FLAGS=flags_copy):
            enable_flag(flag_name)
            self.assertTrue(flag_enabled(flag_name))
            response = self._simulate_cilogon_login(
                new_cilogon_user_data, process=AuthProcess.CONNECT)
            self._assert_successful_cilogin_response(
                response, process=AuthProcess.CONNECT)

            self.assertEqual(User.objects.count(), num_users)
            self.assertEqual(
                SocialAccount.objects.count(), num_social_accounts + 1)
            self.assertEqual(
                EmailAddress.objects.count(), num_email_addresses + 1)

    def test_no_user_identified(self):
        """Test that, when no existing User could be identified from the
        login information, a new one is created, along with associated
        objects."""
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(SocialAccount.objects.count(), 0)
        self.assertEqual(EmailAddress.objects.count(), 0)

        cilogon_user_data = self._cilogon_user_data()
        cilogon_user_data.pop('eppn')
        email = cilogon_user_data['email'].lower()

        response = self._simulate_cilogon_login(cilogon_user_data)
        self._assert_successful_cilogin_response(response)

        self.assertEqual(User.objects.count(), 1)
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            self.fail(f'A User with email {email} should exist.')
        else:
            self.assertEqual(user.username, email)
            self.assertEqual(user.first_name, cilogon_user_data['given_name'])
            self.assertEqual(user.last_name, cilogon_user_data['family_name'])

        self.assertEqual(SocialAccount.objects.count(), 1)
        try:
            SocialAccount.objects.get(
                user=user, uid=cilogon_user_data['sub'],
                provider=self._cilogon_provider)
        except SocialAccount.DoesNotExist:
            self.fail(
                f'A SocialAccount for User {user} should have been created.')

        self.assertEqual(EmailAddress.objects.count(), 1)
        try:
            email_address = EmailAddress.objects.get(user=user, email=email)
        except EmailAddress.DoesNotExist:
            self.fail(f'An EmailAddress with email {email} should exist.')
        else:
            self.assertTrue(email_address.primary)
            self.assertTrue(email_address.verified)

        self._assert_authenticated()

    def test_no_user_identified_invalid_eppn(self):
        """Test that, when no existing User could be identified from the
        login information, and the eppn given does not match a
        EmailAddress, a new User is created, along with associated
        objects."""
        self.assertEqual(User.objects.count(), 0)

        # An EmailAddress does not already exist for eppn.
        eppn = 'user@subdomain.email.com'
        validate_email(eppn)
        self.assertFalse(EmailAddress.objects.filter(email=eppn).exists())

        cilogon_user_data = self._cilogon_user_data(eppn=eppn)
        email = cilogon_user_data['email'].lower()

        response = self._simulate_cilogon_login(cilogon_user_data)
        self._assert_successful_cilogin_response(response)

        self.assertEqual(User.objects.count(), 1)
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            self.fail(f'A User with email {email} should exist.')
        else:
            self.assertEqual(user.username, email)
            self.assertEqual(user.first_name, cilogon_user_data['given_name'])
            self.assertEqual(user.last_name, cilogon_user_data['family_name'])

        self.assertEqual(SocialAccount.objects.count(), 1)
        try:
            SocialAccount.objects.get(
                user=user, uid=cilogon_user_data['sub'],
                provider=self._cilogon_provider)
        except SocialAccount.DoesNotExist:
            self.fail(
                f'A SocialAccount for User {user} should have been created.')

        self.assertEqual(EmailAddress.objects.count(), 1)
        try:
            email_address = EmailAddress.objects.get(user=user, email=email)
        except EmailAddress.DoesNotExist:
            self.fail(f'An EmailAddress with email {email} should exist.')
        else:
            self.assertTrue(email_address.primary)
            self.assertTrue(email_address.verified)

        # An EmailAddress should not have been created for eppn.
        self.assertFalse(EmailAddress.objects.filter(email=eppn).exists())

        self._assert_authenticated()

    def test_existent_social_account(self):
        """Test that, when a matching SocialAccount already exists, the
        User is signed in to the existing account."""
        cilogon_user_data = self._cilogon_user_data()
        email = cilogon_user_data['email'].lower()

        self.assertFalse(EmailAddress.objects.filter(email=email).exists())

        # Sign up
        response = self._simulate_cilogon_login(cilogon_user_data)
        self._assert_successful_cilogin_response(response)

        self._assert_authenticated()

        self.client.logout()

        num_users = User.objects.count()
        num_social_accounts = SocialAccount.objects.count()
        num_email_addresses = EmailAddress.objects.count()

        user = User.objects.get(email=email)
        user.username = 'username'
        user.save()
        last_login = user.last_login

        EmailAddress.objects.get(
            user=user, email=email, verified=True, primary=True)

        SocialAccount.objects.get(
            user=user, uid=cilogon_user_data['sub'],
            provider=self._cilogon_provider)

        # Sign in
        response = self._simulate_cilogon_login(cilogon_user_data)
        self._assert_successful_cilogin_response(response)

        self.assertEqual(User.objects.count(), num_users)
        self.assertEqual(SocialAccount.objects.count(), num_social_accounts)
        self.assertEqual(EmailAddress.objects.count(), num_email_addresses)

        user.refresh_from_db()
        self.assertGreater(user.last_login, last_login)

        self._assert_authenticated()

    def test_one_user_identified_via_email_and_eppn(self):
        """Test that, when a single User is identified via both email
        and eppn, the User is signed in to the existing account."""
        email = 'user@email.com'
        eppn = 'user@subdomain.email.com'
        user = User.objects.create(username='username', email=email)
        EmailAddress.objects.create(
            user=user, email=email, verified=True, primary=True)
        EmailAddress.objects.create(
            user=user, email=eppn, verified=True, primary=False)

        self.assertEqual(SocialAccount.objects.count(), 0)

        cilogon_user_data = self._cilogon_user_data(email=email, eppn=eppn)

        response = self._simulate_cilogon_login(cilogon_user_data)
        self._assert_successful_cilogin_response(response)

        try:
            SocialAccount.objects.get(
                user=user, uid=cilogon_user_data['sub'],
                provider=self._cilogon_provider)
        except SocialAccount.DoesNotExist:
            self.fail(
                f'A SocialAccount for User {user} should have been created.')

        # A new User should not have been created.
        self.assertEqual(User.objects.count(), 1)
        # The number of EmailAddresses should not have increased.
        self.assertEqual(EmailAddress.objects.count(), 2)

        self._assert_authenticated()

    def test_one_user_identified_via_email(self):
        """Test that, when a single User is identified exclusively via
        email, the User is signed in to the existing account."""
        email = 'user@email.com'
        eppn = 'user@subdomain.email.com'
        user = User.objects.create(username='username', email=email)
        EmailAddress.objects.create(
            user=user, email=email, verified=True, primary=True)

        self.assertEqual(SocialAccount.objects.count(), 0)

        cilogon_user_data = self._cilogon_user_data(email=email, eppn=eppn)

        response = self._simulate_cilogon_login(cilogon_user_data)
        self._assert_successful_cilogin_response(response)

        try:
            SocialAccount.objects.get(
                user=user, uid=cilogon_user_data['sub'],
                provider=self._cilogon_provider)
        except SocialAccount.DoesNotExist:
            self.fail(
                f'A SocialAccount for User {user} should have been created.')

        # A new User should not have been created.
        self.assertEqual(User.objects.count(), 1)
        # The number of EmailAddresses should not have increased.
        self.assertEqual(EmailAddress.objects.count(), 1)

        # An EmailAddress should not have been created for eppn.
        self.assertFalse(EmailAddress.objects.filter(email=eppn).exists())

        self._assert_authenticated()

    def test_one_user_identified_via_eppn(self):
        """Test that, when a single User is identified exclusively via
        eppn, the User is signed in to the existing account."""
        email = 'user@email.com'
        eppn = 'user@subdomain.email.com'
        user = User.objects.create(username='username', email=eppn)
        EmailAddress.objects.create(
            user=user, email=eppn, verified=True, primary=True)

        self.assertEqual(SocialAccount.objects.count(), 0)

        cilogon_user_data = self._cilogon_user_data(email=email, eppn=eppn)

        response = self._simulate_cilogon_login(cilogon_user_data)
        self._assert_successful_cilogin_response(response)

        try:
            SocialAccount.objects.get(
                user=user, uid=cilogon_user_data['sub'],
                provider=self._cilogon_provider)
        except SocialAccount.DoesNotExist:
            self.fail(
                f'A SocialAccount for User {user} should have been created.')

        # A new User should not have been created.
        self.assertEqual(User.objects.count(), 1)

        # The number of EmailAddresses should have increased.
        self.assertEqual(EmailAddress.objects.count(), 2)

        # An EmailAddress should have been created for email.
        self.assertTrue(
            EmailAddress.objects.filter(
                user=user, email=email, verified=True, primary=False).exists())

        self._assert_authenticated()

    def test_one_user_identified_but_inactive(self):
        """Test that, when a single User is identified, but the User is
        inactive, they are blocked from logging in, but database objects
        related to the login are still created."""
        email = 'user@email.com'
        eppn = 'user@subdomain.email.com'
        user = User.objects.create(username='username', email=eppn)
        user.is_active = False
        user.save()
        EmailAddress.objects.create(
            user=user, email=eppn, verified=True, primary=True)

        self.assertEqual(SocialAccount.objects.count(), 0)

        cilogon_user_data = self._cilogon_user_data(email=email, eppn=eppn)

        response = self._simulate_cilogon_login(cilogon_user_data)
        self.assertRedirects(response, reverse('account_inactive'))
        self.assertContains(response, 'inactive user account')

        try:
            SocialAccount.objects.get(
                user=user, uid=cilogon_user_data['sub'],
                provider=self._cilogon_provider)
        except SocialAccount.DoesNotExist:
            self.fail(
                f'A SocialAccount for User {user} should have been created.')

        # A new User should not have been created.
        self.assertEqual(User.objects.count(), 1)

        # The number of EmailAddresses should have increased.
        self.assertEqual(EmailAddress.objects.count(), 2)

        # An EmailAddress should have been created for email.
        self.assertTrue(
            EmailAddress.objects.filter(
                user=user, email=email, verified=True, primary=False).exists())

        self._assert_authenticated(negate=True)

    def test_two_users_identified_via_email_and_eppn(self):
        """Test that, when two different Users are identified via email
        and eppn, an error is raised."""
        email = 'user@email.com'
        email_user = User.objects.create(username='email_user', email=email)
        EmailAddress.objects.create(
            user=email_user, email=email, verified=True, primary=True)

        eppn = 'user@subdomain.email.com'
        eppn_user = User.objects.create(username='eppn_user', email=email)
        EmailAddress.objects.create(
            user=eppn_user, email=eppn, verified=True, primary=False)

        self.assertEqual(SocialAccount.objects.count(), 0)

        cilogon_user_data = self._cilogon_user_data(email=email, eppn=eppn)

        response = self._simulate_cilogon_login(cilogon_user_data)
        self.assertIn(
            'Unexpected authentication error.', response.context['message'])

        self.assertEqual(SocialAccount.objects.count(), 0)

        self._assert_authenticated(negate=True)

    def test_identifying_emails_all_unverified(self):
        """Test that, when all the EmailAddresses used to identify the
        User are unverified, """
        email = 'user@email.com'
        eppn = 'user@subdomain.email.com'
        user = User.objects.create(username='username', email=email)
        EmailAddress.objects.create(
            user=user, email=email, verified=False, primary=True)
        EmailAddress.objects.create(
            user=user, email=eppn, verified=False, primary=False)

        self.assertEqual(SocialAccount.objects.count(), 0)

        cilogon_user_data = self._cilogon_user_data(email=email, eppn=eppn)

        self.assertEqual(len(mail.outbox), 0)

        response = self._simulate_cilogon_login(cilogon_user_data)

        self.assertIn('unverified', response.context['message'])

        self.assertEqual(len(mail.outbox), 2)
        expected_from = settings.EMAIL_SENDER
        expected_to = {email, eppn}
        for email in mail.outbox:
            self.assertEqual(email.from_email, expected_from)
            self.assertEqual(len(email.to), 1)
            to = email.to[0]
            self.assertIn(to, expected_to)
            expected_to.remove(to)
            self.assertIn('has not been verified', email.body)

        self._assert_authenticated(negate=True)
