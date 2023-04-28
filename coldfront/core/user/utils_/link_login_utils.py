from django.conf import settings
from django.urls import reverse

from sesame.utils import get_query_string

from coldfront.core.utils.common import build_absolute_url
from coldfront.core.utils.common import import_from_settings
from coldfront.core.utils.mail import send_email_template


class UserLoginLinkIneligible(Exception):
    pass


def login_token_url(user):
    """Return a Django Sesame login link for the given User."""
    return build_absolute_url(reverse('link-login') + get_query_string(user))


def send_login_link_email(email_address):
    """Send an email containing a login link to the given
    EmailAddress."""
    email_enabled = import_from_settings('EMAIL_ENABLED', False)
    if not email_enabled:
        return

    subject = 'Login Link'
    template_name = 'email/login/login_link.txt'
    context = {
        'PORTAL_NAME': settings.PORTAL_NAME,
        'login_url': login_token_url(email_address.user),
        'login_link_max_age_minutes': (
            import_from_settings('SESAME_MAX_AGE') // 60),
        'signature': import_from_settings('EMAIL_SIGNATURE', ''),
    }

    sender = import_from_settings('EMAIL_SENDER')
    receiver_list = [email_address.email, ]

    send_email_template(subject, template_name, context, sender, receiver_list)


def send_login_link_ineligible_email(email_address, reason):
    """Send an email containing a reason explaining why the User with
    the given EmailAddress is ineligible to receive a login link."""
    email_enabled = import_from_settings('EMAIL_ENABLED', False)
    if not email_enabled:
        return

    subject = 'Ineligible for Login Link'
    template_name = 'email/login/login_link_ineligible.txt'
    context = {
        'PORTAL_NAME': settings.PORTAL_NAME,
        'reason': reason,
        'signature': import_from_settings('EMAIL_SIGNATURE', ''),
    }

    sender = import_from_settings('EMAIL_SENDER')
    receiver_list = [email_address.email, ]

    send_email_template(subject, template_name, context, sender, receiver_list)


def validate_user_eligible_for_login_link(user):
    """Return None if the given User is eligible to log in using a link.
    Otherwise, raise an exception with a user-facing message explaining
    why the user is ineligible."""
    # Inactive users
    if not user.is_active:
        raise UserLoginLinkIneligible(
            'Inactive users are disallowed from logging in using a link.')
    # Staff users and superusers
    if user.is_staff or user.is_superuser:
        raise UserLoginLinkIneligible(
            'For security reasons, portal staff are disallowed from logging in '
            'using a link.')
