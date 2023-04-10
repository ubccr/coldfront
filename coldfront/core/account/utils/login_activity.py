import pytz

from django.conf import settings
from django.http.request import HttpRequest
from django.urls import reverse

from allauth.account.models import EmailAddress
from allauth.account.models import EmailConfirmationHMAC
from user_agents import parse

from coldfront.core.utils.common import build_absolute_url
from coldfront.core.utils.common import import_from_settings
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.mail import send_email_template


class LoginActivityVerifier(object):
    """A class that can email an unverified EmailAddress, notifying the
    user that a blocked login attempt was made using it and asking the
    user to confirm that the attempt was made by them, which will verify
    the address."""

    def __init__(self, request, email_address, request_login_method_str):
        """Validate arguments.

        Parameters
            - request (HttpRequest): the request object for the login
            - email_address (EmailAddress): an unverified EmailAddress
              instance
            - request_login_method_str (str): A str describing the
              method that was used to attempt to log in (e.g.,
              'CILogon - Lawrence Berkeley National Laboratory' or
              'Login Link Request')
        """
        assert isinstance(request, HttpRequest)
        assert isinstance(email_address, EmailAddress)
        assert not email_address.verified
        assert isinstance(request_login_method_str, str)

        self._request = request
        self._email_address = email_address
        self._request_time_str = self.get_display_timezone_now_str()
        self._request_user_agent_str = self.get_request_user_agent_str()
        self._request_login_method_str = request_login_method_str

    @staticmethod
    def get_display_timezone_now_str():
        """Return a time string for the current time in the display time
        zone (e.g., 'January 1, 1970 at 12:00 PM (UTC)')."""
        display_time_zone = pytz.timezone(settings.DISPLAY_TIME_ZONE)
        utc_now = utc_now_offset_aware()
        display_format = '%B %-d, %Y at %-I:%M %p (%Z)'
        return display_time_zone.normalize(utc_now).strftime(display_format)

    def get_request_user_agent_str(self):
        """Given an HTTP request, return a str describing the user agent
        that made the request (e.g., 'Chrome on Mac OS X')."""
        user_agent_header = self._request.headers.get('user-agent', '')
        if not user_agent_header:
            return 'Unknown Browser and OS'
        user_agent = parse(user_agent_header)
        return f'{user_agent.browser.family} on {user_agent.os.family}'

    def login_activity_verification_url(self):
        """Return an absolute URL to the view for verifying the
        EmailAddress.

        This is adapted from allauth.account.adapter.
        DefaultAccountAdapter.get_email_confirmation_url."""
        hmac = EmailConfirmationHMAC(self._email_address)
        return build_absolute_url(
            reverse('account_confirm_email', args=[hmac.key]))

    def send_email(self):
        """Email the user, asking them to confirm the login attempt by
        clicking on a link, which will verify the address."""
        email_enabled = import_from_settings('EMAIL_ENABLED', False)
        if not email_enabled:
            return

        subject = 'Verify Login Activity'
        template_name = 'email/login/verify_login_activity.txt'
        context = {
            'PORTAL_NAME': settings.PORTAL_NAME,
            'email_address': self._email_address.email,
            'request_time_str': self._request_time_str,
            'request_user_agent_str': self._request_user_agent_str,
            'request_login_method_str': self._request_login_method_str,
            'support_email': settings.CENTER_HELP_EMAIL,
            'verification_url': self.login_activity_verification_url(),
            'signature': import_from_settings('EMAIL_SIGNATURE', ''),
        }

        sender = settings.EMAIL_SENDER
        receiver_list = [self._email_address.email]

        send_email_template(
            subject, template_name, context, sender, receiver_list)
