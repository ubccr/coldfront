from coldfront.core.user.models import ExpiringToken
from datetime import datetime
from datetime import timezone
from rest_framework import exceptions
from rest_framework.authentication import TokenAuthentication


class ExpiringTokenAuthentication(TokenAuthentication):

    model = ExpiringToken

    def authenticate_credentials(self, key):
        model = self.get_model()
        try:
            token = model.objects.select_related('user').get(key=key)
        except model.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid token.')

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed('User inactive or deleted.')

        if is_token_expired(token):
            raise exceptions.AuthenticationFailed('Expired token.')

        return token.user, token


def is_token_expired(token):
    """Return whether or not the given token is older than its
    expiration time."""
    return token.expiration and token.expiration < datetime.now(timezone.utc)
