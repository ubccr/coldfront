import logging

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic.edit import FormView

from allauth.account.models import EmailAddress
from sesame.views import LoginView

from coldfront.core.account.utils.login_activity import LoginActivityVerifier
from coldfront.core.user.forms_.link_login_forms import RequestLoginLinkForm
from coldfront.core.user.utils_.link_login_utils import send_login_link_email
from coldfront.core.user.utils_.link_login_utils import send_login_link_ineligible_email
from coldfront.core.user.utils_.link_login_utils import UserLoginLinkIneligible
from coldfront.core.user.utils_.link_login_utils import validate_user_eligible_for_login_link
from coldfront.core.utils.common import import_from_settings


logger = logging.getLogger(__name__)


class RequestLoginLinkView(FormView):
    """A view that sends a login link to the user with the provided
    email address, if any."""

    form_class = RequestLoginLinkForm
    template_name = 'user/request_login_link.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(reverse('home'))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        """If a corresponding EmailAddress exists, send an email (with a
        login link, further instructions, or an explanation) to it.

        In all cases, display an acknowledging message with the same
        text, to avoid leaking information."""
        email = form.cleaned_data.get('email')
        email_address = self._validate_email_address(email)
        if email_address:
            if not email_address.verified:
                request_login_method_str = 'Link Login Request'
                verifier = LoginActivityVerifier(
                    self.request, email_address, request_login_method_str)
                verifier.send_email()
            else:
                try:
                    validate_user_eligible_for_login_link(email_address.user)
                except UserLoginLinkIneligible as e:
                    reason = str(e)
                    send_login_link_ineligible_email(email_address, reason)
                else:
                    send_login_link_email(email_address)
        self._send_ack_message()
        return super().form_valid(form)

    @staticmethod
    def ack_message():
        """Return an acknowledging message explaining that a link or
        further instructions were (conditionally) sent."""
        login_link_max_age_minutes = (
            import_from_settings('SESAME_MAX_AGE') // 60)
        return (
            f'If the email address you entered corresponds to an existing '
            f'user, please check the address for a login link or further '
            f'instructions. Note that this link will expire in '
            f'{login_link_max_age_minutes} minutes.')

    @staticmethod
    def get_success_url():
        return reverse('request-login-link')

    def _send_ack_message(self):
        """Send an acknowledging message to the user."""
        messages.success(self.request, self.ack_message())

    def _validate_email_address(self, email):
        """Return an EmailAddress object corresponding to the given
        address (str) if one exists. Otherwise, return None. Write user
        and log messages as needed."""
        try:
            return EmailAddress.objects.get(email=email)
        except EmailAddress.DoesNotExist:
            return None
        except EmailAddress.MultipleObjectsReturned:
            logger.error(
                f'Unexpectedly found multiple EmailAddresses for email '
                f'{email}.')
            message = (
                'Unexpected server error. Please contact an administrator.')
            messages.error(self.request, message)
            return None


class LinkLoginView(LoginView):
    """A subclass of Django Sesame's login view, with custom logic."""

    def login_failed(self):
        """Send an error message to the user and write to the log before
        deferring to parent logic."""
        message = 'Invalid or expired login link.'
        messages.error(self.request, message)
        logger.warning(
            'A user failed to log in using an invalid or expired login link.')
        return super().login_failed()

    def login_success(self):
        """Send a success message to the user and write to the log
        before deferring to parent logic.

        Note: Users should not be activated, so that explicitly blocked
        users do not have a path to reactivation.
        """
        user = self.request.user
        message = f'Successfully signed in as {user.username}.'
        messages.success(self.request, message)
        logger.warning(
            f'User {user.pk} ({user.username}) logged in using a login link.')

        return super().login_success()
