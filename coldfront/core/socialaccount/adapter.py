from allauth.account.models import EmailAddress
from allauth.account.utils import user_email as user_email_func
from allauth.account.utils import user_field
from allauth.account.utils import user_username
from allauth.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.utils import valid_email_or_none
from coldfront.core.account.utils.login_activity import LoginActivityVerifier
from collections import defaultdict
from django.conf import settings
from django.http import HttpResponseBadRequest
from django.http import HttpResponseServerError
from django.template.loader import render_to_string
import logging


logger = logging.getLogger(__name__)


class CILogonAccountAdapter(DefaultSocialAccountAdapter):
    """An adapter that adjusts handling for the CILogon provider."""

    def populate_user(self, request, sociallogin, data):
        """Handle logins using the CILogon provider differently. In
        particular, use the given email address as the username; raise
        an error if one is not provided. Handle logins using other
        providers normally."""
        # Attempt to retrieve identifying information for logging purposes.
        try:
            provider = sociallogin.account.provider
        except AttributeError:
            provider = 'unknown'
        try:
            user_uid = sociallogin.account.uid
        except AttributeError:
            user_uid = 'unknown'

        if provider == 'cilogon':
            first_name = data.get('first_name', '')
            last_name = data.get('last_name', '')
            email = data.get('email')

            validated_email = valid_email_or_none(email)
            if not validated_email:
                log_message = (
                    f'Provider {provider} did not provide an email address '
                    f'for User with UID {user_uid}.')
                logger.error(log_message)
                self._raise_server_error(self._get_auth_error_message())
            validated_email = validated_email.lower()

            user = sociallogin.user
            user_username(user, validated_email)
            user_email_func(user, validated_email)
            user_field(user, 'first_name', first_name)
            user_field(user, 'last_name', last_name)
            return user

        return super().populate_user(request, sociallogin, data)

    def pre_social_login(self, request, sociallogin):
        """At this point, the user is authenticated by a provider. If
        the provider is not CILogon, do nothing. Otherwise, if this
        provider account is not connected to a local account, attempt to
        connect them. In particular, if there is a User with a verified
        EmailAddress matching one of those given by the provider,
        connect the two accounts.

        Note that login is blocked outside (after) this method if the
        user is inactive.

        Adapted from:
        https://github.com/pennersr/django-allauth/issues/418#issuecomment-137259550
        """
        # Attempt to retrieve identifying information for logging purposes.
        try:
            provider = sociallogin.account.provider
        except AttributeError:
            provider = 'unknown'
        try:
            user_uid = sociallogin.account.uid
        except AttributeError:
            user_uid = 'unknown'
        try:
            user_email = sociallogin.user.email
        except AttributeError:
            user_email = 'unknown'

        # Do nothing if the provider is not CILogon.
        if provider != 'cilogon':
            return

        # If a SocialAccount already exists, meaning the provider account is
        # connected to a local account, proceed with login.
        if sociallogin.is_existing:
            return

        # If the provider does not provide any addresses, raise an error.
        provider_addresses = sociallogin.email_addresses
        if not provider_addresses:
            log_message = (
                f'Provider {provider} did not provide any email addresses for '
                f'User with email {user_email} and UID {user_uid}.')
            logger.error(log_message)
            self._raise_server_error(self._get_auth_error_message())

        # SOCIALACCOUNT_PROVIDERS['cilogon']['VERIFIED_EMAIL'] should be True,
        # so all provider-given addresses should be interpreted as verified.
        verified_provider_addresses = [
            address for address in provider_addresses if address.verified]
        # If, for whatever reason, they are not, raise an error.
        if not verified_provider_addresses:
            log_message = (
                f'None of the email addresses in '
                f'[{", ".join(provider_addresses)}] are verified.')
            logger.error(log_message)
            self._raise_server_error(self._get_auth_error_message())

        # Fetch EmailAddresses matching those given by the provider, divided by
        # the associated User.
        matching_addresses_by_user = defaultdict(set)
        for address in verified_provider_addresses:
            try:
                email_address = EmailAddress.objects.get(
                    email__iexact=address.email)
            except EmailAddress.DoesNotExist:
                continue
            matching_addresses_by_user[email_address.user].add(email_address)

        # If no Users were found, proceed with signup. If exactly one was
        # found, perform further checks. If more than one was found, raise an
        # error.
        if not matching_addresses_by_user:
            return
        elif len(matching_addresses_by_user) == 1:
            user = next(iter(matching_addresses_by_user))
            addresses = matching_addresses_by_user[user]
            if any([a.verified for a in addresses]):
                # After this, allauth.account.adapter.pre_login blocks login if
                # the user is inactive. Regardless of that, connect the user
                # (and trigger signals for creating EmailAddresses).
                self._connect_user(
                    request, sociallogin, provider, user, user_email, user_uid)
            else:
                self._block_login_for_verification(
                    request, sociallogin, provider, user, user_email, user_uid,
                    addresses)
        else:
            user_pks = sorted([user.pk for user in matching_addresses_by_user])
            log_message = (
                f'Unexpectedly found multiple Users ([{", ".join(user_pks)}]) '
                f'that had email addresses matching those provided by '
                f'provider {provider} for User with email {user_email} and '
                f'UID {user_uid}.')
            logger.error(log_message)
            self._raise_server_error(self._get_auth_error_message())

    def _block_login_for_verification(self, request, sociallogin, provider,
                                      user, user_email, user_uid,
                                      email_addresses):
        """Block the login attempt and send verification emails to the
        given EmailAddresses."""
        log_message = (
            f'Found only unverified email addresses associated with local User '
            f'{user.pk} matching those given by provider {provider} for User '
            f'with email {user_email} and UID {user_uid}.')
        logger.warning(log_message)

        try:
            cilogon_idp = sociallogin.serialize()[
                'account']['extra_data']['idp_name']
            request_login_method_str = f'CILogon - {cilogon_idp}'
        except Exception as e:
            logger.exception(f'Failed to determine CILogon IDP. Details:\n{e}')
            request_login_method_str = 'CILogon'
        for email_address in email_addresses:
            verifier = LoginActivityVerifier(
                request, email_address, request_login_method_str)
            verifier.send_email()

        message = (
            'You are attempting to log in using an email address associated '
            'with an existing user, but it is unverified. Please check the '
            'address for a verification email.')
        self._raise_client_error(message)

    @staticmethod
    def _connect_user(request, sociallogin, provider, user, user_email,
                      user_uid):
        """Connect the provider account to the User's account in the
        database."""
        sociallogin.connect(request, user)
        log_message = (
            f'Successfully connected data for User with email {user_email} and '
            f'UID {user_uid} from provider {provider} to local User {user.pk}.')
        logger.info(log_message)

    @staticmethod
    def _get_auth_error_message():
        """Return the generic message the user should receive if
        authentication-related errors occur."""
        return (
            f'Unexpected authentication error. Please contact '
            f'{settings.CENTER_HELP_EMAIL} for further assistance.')

    @staticmethod
    def _raise_client_error(message):
        """Raise an ImmediateHttpResponse with a client error and the
        given message."""
        template = 'error_with_message.html'
        html = render_to_string(template, context={'message': message})
        response = HttpResponseBadRequest(html)
        raise ImmediateHttpResponse(response)

    @staticmethod
    def _raise_server_error(message):
        """Raise an ImmediateHttpResponse with a server error and the
        given message."""
        template = 'error_with_message.html'
        html = render_to_string(template, context={'message': message})
        response = HttpResponseServerError(html)
        raise ImmediateHttpResponse(response)
