from coldfront.core.user.models import EmailAddress
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User


class EmailAddressBackend(BaseBackend):
    """An authentication backend that allows a user to authenticate
    using any of their verified EmailAddress objects."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            email_address = EmailAddress.objects.select_related(
                'user').get(email=username)
        except EmailAddress.DoesNotExist:
            return None
        user = email_address.user

        # If the EmailAddress exists, but is not verified, send a verification
        # email to it. Only do this if the user is already active; otherwise,
        # a separate account activation email will handle email verification.
        if user.is_active and not email_address.is_verified:
            # TODO.
            return None

        if user.check_password(password):
            return user
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None
