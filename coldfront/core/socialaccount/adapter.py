from allauth.account.models import EmailAddress
from allauth.account.utils import user_email as user_email_func
from allauth.account.utils import user_username
from allauth.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.providers.base import AuthProcess
from allauth.utils import valid_email_or_none
from coldfront.core.account.utils.login_activity import LoginActivityVerifier
from coldfront.core.utils.context_processors import portal_and_program_names
from collections import defaultdict
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import HttpResponseBadRequest
from django.http import HttpResponseServerError
from django.template.loader import render_to_string
from django.urls import reverse
from flags.state import flag_enabled
import logging


logger = logging.getLogger(__name__)


class CILogonAccountAdapter(DefaultSocialAccountAdapter):
    """An adapter that adjusts handling for the CILogon provider."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._flag_multiple_email_addresses_allowed = flag_enabled(
            'MULTIPLE_EMAIL_ADDRESSES_ALLOWED')

    def populate_user(self, request, sociallogin, data):
        """Handle logins using the CILogon provider differently. In
        particular, raise an error if no email address is provided,
        ensure that it is set in lowercase, and use it as the username.
        Handle logins using other providers normally."""
        user = super().populate_user(request, sociallogin, data)

        provider = sociallogin.account.provider
        if provider == 'cilogon':
            validated_email = valid_email_or_none(user.email)
            if not validated_email:
                log_message = (
                    f'Provider {provider} did not provide an email address for '
                    f'user with UID {sociallogin.account.uid}.')
                logger.error(log_message)
                self._raise_server_error(self._get_auth_error_message())
            validated_email = validated_email.lower()
            user_email_func(user, validated_email)
            user_username(user, validated_email)

        return user

    def get_connect_redirect_url(self, request, socialaccount):
        """
        Returns the default URL to redirect to after successfully
        connecting a social account.
        """
        if self._flag_multiple_email_addresses_allowed:
            url = reverse('socialaccount_connections')
        else:
            url = reverse('home')
        return url

    def pre_social_login(self, request, sociallogin):
        """At this point, the user is authenticated by a provider.
            - Log the user in if the provider is already connected to
              a local User.
            - If possible, connect to a single local User based on
              provider-given information, raising errors as needed.
            - If the user is wholly now, create a new local User.

        Note that login is blocked outside (after) this method if the
        local User is inactive.

        Adapted from:
        https://github.com/pennersr/django-allauth/issues/418#issuecomment-137259550

        Parameters:
            - request: HTTP request object
            - sociallogin: django-allauth SocialLogin object

        Returns: None

        Raises:
            - ImmediateHttpResponse (bad request or server error)
        """
        provider = sociallogin.account.provider
        user_uid = sociallogin.account.uid
        user_email = sociallogin.user.email

        # Do nothing if the provider is not CILogon.
        if provider != 'cilogon':
            return

        # If users are not allowed to have multiple emails, block new
        # SocialAccount connections to existing local accounts.
        if not self._flag_multiple_email_addresses_allowed:
            self._block_social_account_connection(sociallogin)

        # If a SocialAccount already exists, meaning the provider account is
        # connected to a local account, proceed with login.
        if sociallogin.is_existing:
            return

        # Try to identify a single user from EmailAddresses, based on
        # information given by the provider, along with the identifying
        # addresses.
        user, addresses = self._identify_user_and_email_addresses(
            sociallogin, provider, user_email, user_uid)

        # No single User could be identified. Proceed with sign up.
        if user is None:
            return

        # A single User could be identified, but all email addresses used to do
        # so were unverified. Block the login and request email verification.
        if not any([a.verified for a in addresses]):
            self._block_login_for_verification(
                request, sociallogin, provider, user, user_email, user_uid,
                addresses)

        # A single User could be identified from at least one verified email
        # address. Connect to that User.
        self._connect_user(
            request, sociallogin, provider, user, user_email, user_uid)

    def _block_login_for_verification(self, request, sociallogin, provider,
                                      user, user_email, user_uid,
                                      email_addresses):
        """Block the login attempt and send verification emails to the
        given EmailAddresses."""
        log_message = (
            f'Found only unverified email addresses associated with local User '
            f'{user.pk} matching those given by provider {provider} for user '
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

    def _block_social_account_connection(self, sociallogin):
        """Raise a client error if the user is attempting to connect
        another SocialAccount to their account (as opposed to logging in
        with an existing one)."""
        if sociallogin.state.get('process', None) == AuthProcess.CONNECT:
            message = (
                'You may not connect more than one third-party account to your '
                'portal account.')
            self._raise_client_error(message)

    @staticmethod
    def _connect_user(request, sociallogin, provider, user, user_email,
                      user_uid):
        """Connect the provider account to the User's account in the
        database."""
        sociallogin.connect(request, user)
        log_message = (
            f'Successfully connected data for user with email {user_email} and '
            f'UID {user_uid} from provider {provider} to local User {user.pk}.')
        logger.info(log_message)

    @staticmethod
    def _get_auth_error_message():
        """Return the generic message the user should receive if
        authentication-related errors occur."""
        return (
            f'Unexpected authentication error. Please contact '
            f'{settings.CENTER_HELP_EMAIL} for further assistance.')

    def _identify_user_and_email_addresses(self, sociallogin, provider,
                                           user_email, user_uid):
        """Attempt to identify a single existing User from
        provider-given email information. If able, return the User and a
        list of EmailAddress objects used to identify it, else (None,
        None). Raise a server error in some unexpected cases."""
        user_by_email, user_by_email_email_addresses = \
            self._identify_user_by_email(
                sociallogin, provider, user_email, user_uid)
        user_by_eppn, user_by_eppn_email_addresses = \
            self._identify_user_by_eppn(sociallogin)

        if user_by_email and user_by_eppn:
            if user_by_email.pk != user_by_eppn.pk:
                log_message = (
                    f'Found two different local Users from information '
                    f'provided by provider {provider} for user with email '
                    f'{user_email} and UID {user_uid} (email lookup: '
                    f'{user_by_email.pk}, eppn lookup: {user_by_eppn.pk}).')
                logger.error(log_message)
                self._raise_server_error(self._get_auth_error_message())
            else:
                # The sets of EmailAddresses used to identify the user may be
                # different, so return their union.
                all_email_addresses = list(
                    set.union(
                        set(user_by_email_email_addresses),
                        set(user_by_eppn_email_addresses)))
                return user_by_email, all_email_addresses
        elif user_by_email:
            return user_by_email, user_by_email_email_addresses
        elif user_by_eppn:
            eppn = user_by_eppn_email_addresses[0].email
            log_message = (
                f'Found a local User ({user_by_eppn.pk}) from eppn ({eppn}), '
                f'and not from emails, provided by provider {provider} for '
                f'user with email {user_email} and UID {user_uid}.')
            logger.warning(log_message)
            return user_by_eppn, user_by_eppn_email_addresses
        return None, None

    def _identify_user_by_email(self, sociallogin, provider, user_email,
                                user_uid):
        """Attempt to identify a User using provider-given EmailAddress
        objects.
            - 0 identified: return None, None.
            - 1 identified: return the User and a list of the matching
              EmailAddress objects.
            - 2+ identified: raise a server error."""
        verified_provider_addresses = self._validate_provider_email_addresses(
            sociallogin, provider, user_email, user_uid)

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

        if not matching_addresses_by_user:
            return None, None
        elif len(matching_addresses_by_user) == 1:
            user = next(iter(matching_addresses_by_user))
            addresses = matching_addresses_by_user[user]
            return user, addresses
        else:
            user_pks = sorted([user.pk for user in matching_addresses_by_user])
            log_message = (
                f'Unexpectedly found multiple Users ([{", ".join(user_pks)}]) '
                f'that had email addresses matching those provided by '
                f'provider {provider} for user with email {user_email} and '
                f'UID {user_uid}.')
            logger.error(log_message)
            self._raise_server_error(self._get_auth_error_message())

    @staticmethod
    def _identify_user_by_eppn(sociallogin):
        """Attempt to identify a User using an "eppn" field potentially
        given by the provider.
            - 0 identified: return None, None.
            - 1 identified: return the User and a single-item list
              containing the matching EmailAddress object

        There are no guarantees that the "eppn" field is a valid email
        address, even if it is in the format of an email address. Only
        if it matches an existing EmailAddress object can it be assumed
        that it is a valid address."""
        login_extra_data = sociallogin.serialize()['account']['extra_data']
        if 'eppn' not in login_extra_data:
            return None, None
        eppn = login_extra_data['eppn'].lower()

        try:
            validate_email(eppn)
        except ValidationError:
            return None, None

        try:
            email_address = EmailAddress.objects.get(email=eppn)
        except EmailAddress.DoesNotExist:
            return None, None

        return email_address.user, [email_address]

    def _raise_client_error(self, message):
        """Raise an ImmediateHttpResponse with a client error and the
        given message."""
        self._raise_error(HttpResponseBadRequest, message)

    @staticmethod
    def _raise_error(response_class, message):
        """Raise an ImmediateHttpResponse with an error HttpResponse
        class (e.g., HttpResponseBadRequest or HttpResponseServerError)
        error and the given message."""
        template = 'error_with_message.html'
        context = {'message': message, **portal_and_program_names(None)}
        html = render_to_string(template, context=context)
        response = response_class(html)
        raise ImmediateHttpResponse(response)

    def _raise_server_error(self, message):
        """Raise an ImmediateHttpResponse with a server error and the
        given message."""
        self._raise_error(HttpResponseServerError, message)

    def _validate_provider_email_addresses(self, sociallogin, provider,
                                           user_email, user_uid):
        """Process email addresses given by the provider. Raise a server
        error if none are given, or if none are verified. Raise a list
        of verified addresses."""
        provider_addresses = sociallogin.email_addresses
        num_provider_addresses = len(provider_addresses)
        # If the provider does not provide any addresses, raise an error.
        if num_provider_addresses == 0:
            log_message = (
                f'Provider {provider} did not provide any email addresses for '
                f'User with email {user_email} and UID {user_uid}.')
            logger.error(log_message)
            self._raise_server_error(self._get_auth_error_message())
        # In general, it is expected that a provider will only give one address.
        # If multiple are given, allow all of them to be associated with the
        # user (agnostic of whether users are allowed to have multiple), but log
        # a warning.
        elif num_provider_addresses > 1:
            log_message = (
                f'Provider {provider} provided more than one email address for '
                f'User with email {user_email} and UID {user_uid}: '
                f'{", ".join(provider_addresses)}.')
            logger.warning(log_message)

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

        return verified_provider_addresses
