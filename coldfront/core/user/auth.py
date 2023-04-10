from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User

from allauth.account.models import EmailAddress
from sesame.backends import ModelBackend as BaseSesameBackend

from coldfront.core.user.utils import send_email_verification_email
from coldfront.core.user.utils_.link_login_utils import UserLoginLinkIneligible
from coldfront.core.user.utils_.link_login_utils import validate_user_eligible_for_login_link

import logging


logger = logging.getLogger(__name__)


class EmailAddressBackend(BaseBackend):
    """An authentication backend that allows a user to authenticate
    using any of their verified EmailAddress objects."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            return None
        username = username.lower()
        try:
            email_address = EmailAddress.objects.select_related(
                'user').get(email=username)
        except EmailAddress.DoesNotExist:
            return None
        user = email_address.user

        # If the EmailAddress exists, but is not verified, send a verification
        # email to it. Only do this if the user is already active; otherwise,
        # a separate account activation email will handle email verification.
        if user.is_active and not email_address.verified:
            try:
                send_email_verification_email(email_address)
            except Exception as e:
                message = 'Failed to send verification email. Details:'
                logger.error(message)
                logger.exception(e)
            return None

        if user.check_password(password):
            return user
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None


class SesameBackend(BaseSesameBackend):
    """A subclass of django-sesame's ModelBackend that limits who is
    eligible to log in using tokens."""

    def user_can_authenticate(self, user):
        try:
            validate_user_eligible_for_login_link(user)
        except UserLoginLinkIneligible as e:
            message = (
                f'User {user.username} was blocked from Sesame authentication '
                f'because: {str(e)}')
            logger.info(message)
            return False
        return True
