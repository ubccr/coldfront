import logging

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic.edit import FormView

from allauth.account.models import EmailAddress
from sesame.views import LoginView

from coldfront.core.user.forms_.link_login_forms import RequestLoginLinkForm
from coldfront.core.user.utils import send_login_link_email
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
        """If the email address belongs to a user, send a login link to
        it."""
        email = form.cleaned_data.get('email')
        email_address = self._validate_email_address(email)
        if email_address:
            send_login_link_email(email_address)
        self._send_success_message()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('request-login-link')

    def _send_success_message(self):
        """Send a success message to the user explaining that a link was
        (conditionally) sent."""
        login_link_max_age_minutes = (
            import_from_settings('SESAME_MAX_AGE') // 60)
        message = (
            f'If the email address you entered corresponds to an existing '
            f'user, please check the address for a login link. Note that this '
            f'link will expire in {login_link_max_age_minutes} minutes.')
        messages.success(self.request, message)

    def _validate_email_address(self, email):
        """Return an EmailAddress object corresponding to the given
        address (str) if one exists. Otherwise, return None. Write user
        and log messages as needed."""
        email_address = None
        try:
            email_address = EmailAddress.objects.get(email=email)
        except EmailAddress.DoesNotExist:
            pass
        except EmailAddress.MultipleObjectsReturned:
            logger.error(
                f'Unexpectedly found multiple EmailAddresses for email '
                f'{email}.')
            message = (
                'Unexpected server error. Please contact an administrator.')
            messages.error(self.request, message)
        return email_address


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
        """Activate the user if needed, send a success message to the
        user, and write to the log before deferring to parent logic."""
        user = self.request.user
        if not user.is_active:
            user.is_active = True
            user.save()

        message = f'Successfully signed in as {user.username}.'
        messages.success(self.request, message)
        logger.warning(
            f'User {user.pk} ({user.username}) logged in using a login link.')

        return super().login_success()
