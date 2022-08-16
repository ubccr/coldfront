from collections import deque
import logging

from django.contrib import messages
from django.contrib.auth.models import User
from django.db import transaction
from django.dispatch import receiver

from allauth.socialaccount.models import EmailAddress
from allauth.socialaccount.models import SocialLogin
from allauth.socialaccount.providers.base import AuthProcess
from allauth.socialaccount.signals import social_account_added
from allauth.socialaccount.signals import social_account_updated


logger = logging.getLogger(__name__)


@receiver(social_account_added)
@receiver(social_account_updated)
def handle_social_account_added_or_updated(sender, **kwargs):
    """When a SocialAccount (previously-connected or otherwise) is
    connected to a user's local account, create or update EmailAddress
    instances for the addresses given by the provider, setting them as
    verified."""
    request = kwargs['request']
    social_login = kwargs['sociallogin']
    if social_login.state['process'] == AuthProcess.CONNECT:
        try:
            set_verified_email_addresses_from_social_login(social_login)
        except Exception as e:
            message = (
                'Failed to automatically create verified email addresses '
                'from the connected account. Please do so in the User '
                'Profile.')
            messages.error(request, message)


def set_verified_email_addresses_from_social_login(social_login):
    """Given a SocialLogin, which includes a list of EmailAddress
    instances (not yet saved to the database), create or update
    EmailAddress objects in the database, setting them as verified.

    When a User connects a SocialAccount to their local account, the
    email addresses given by the underlying provider should be treated
    as verified, since the currently-authenticated user was able to
    complete the provider's authentication flow.

    If any address is already associated with a different user, raise an
    error."""
    assert isinstance(social_login, SocialLogin)

    email_addresses = social_login.email_addresses
    user = User.objects.get(pk=social_login.user.pk)
    account = social_login.account

    # Transform all emails to lowercase.
    for email_address in email_addresses:
        email_address.email = email_address.email.lower()

    existent, nonexistent = [], []
    for email_address in email_addresses:
        matching_objs = EmailAddress.objects.filter(
            email__iexact=email_address.email)
        if matching_objs.exists():
            existent.append(matching_objs.first())
        else:
            nonexistent.append(email_address)

    for email_address in existent:
        if email_address.user != user:
            message = (
                f'Account connection of User {user.pk} and provider '
                f'{account.provider} failed because one of the provided email '
                f'addresses ({email_address.pk}) is already associated with a '
                f'different user ({email_address.user.pk}).')
            logger.error(message)
            raise Exception(
                f'Account connection failed due to a provided email address '
                f'({email_address.email}) already being associated with a '
                f'different user.')

    # A list of tuples of the form (logging_method_name, message_to_log).
    log_queue = deque()

    try:
        with transaction.atomic():
            for email_address in existent:
                if not email_address.verified:
                    email_address.verified = True
                    email_address.save()
                    message = (
                        f'Verified EmailAddress {email_address.pk} '
                        f'({email_address.email}) when connecting an account '
                        f'for User {user.pk}.')
                    log_queue.append(('info', message))
            for email_address in nonexistent:
                created_address = EmailAddress.objects.create(
                    user=user,
                    email=email_address.email,
                    verified=True,
                    primary=False)
                message = (
                    f'Created verified EmailAddress {created_address.pk} '
                    f'({created_address.email}) when connecting an account '
                    f'for User {user.pk}.')
                log_queue.append(('info', message))
    except Exception as e:
        logger.exception(
            f'Failed to set EmailAddresses as verified. Details:\n{e}')
        raise e
    else:
        while log_queue:
            log_method, log_message = log_queue.popleft()
            getattr(logger, log_method)(log_message)
