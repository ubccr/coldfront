# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.utils import timezone
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.permissions import SAFE_METHODS, BasePermission, DjangoObjectPermissions

from coldfront.users.constants import TOKEN_HEADER_PREFIX, TOKEN_PREFIX
from coldfront.users.models import Token


class TokenAuthentication(BaseAuthentication):
    """
    A custom authentication scheme which enforces Token expiration times.
    """

    model = Token

    def authenticate(self, request):
        # Authorization header is not present; ignore
        if not (auth := get_authorization_header(request).split()):
            return None
        # Unrecognized header; ignore
        if auth[0].lower() != TOKEN_HEADER_PREFIX.lower().encode():
            return None
        # Check for extraneous token content
        if len(auth) != 2:
            raise exceptions.AuthenticationFailed(
                f'Invalid authorization header: Must be in the form "{TOKEN_HEADER_PREFIX} <key>.<token>"'
            )
        # Extract the key & token plaintext from the auth header
        try:
            auth_value = auth[1].decode()
        except UnicodeError:
            raise exceptions.AuthenticationFailed("Invalid authorization header: Token contains invalid characters")

        # Infer token version from presence or absence of prefix
        if not auth_value.startswith(TOKEN_PREFIX):
            raise exceptions.AuthenticationFailed("Invalid authorization header: invalid token prefix")

        auth_value = auth_value.removeprefix(TOKEN_PREFIX)
        try:
            key, plaintext = auth_value.split(".", 1)
        except ValueError:
            raise exceptions.AuthenticationFailed("Invalid authorization header: Could not parse key from token")

        # Look for a matching token in the database
        try:
            # Fetch token by key, then validate the plaintext
            token = Token.objects.prefetch_related("user").get(key=key)
            if not token.validate(plaintext):
                # Key is valid but plaintext is not. Raise DoesNotExist to guard against key enumeration.
                raise Token.DoesNotExist()
        except Token.DoesNotExist:
            raise exceptions.AuthenticationFailed("Invalid token")

        # Enforce the Token is enabled
        if not token.enabled:
            raise exceptions.AuthenticationFailed("Token disabled")

        # Enforce the Token's expiration time, if one has been set.
        if token.is_expired:
            raise exceptions.AuthenticationFailed("Token expired")

        # Update last used, but only once per minute at most. This reduces write load on the database
        if not token.last_used or (timezone.now() - token.last_used).total_seconds() > 60:
            Token.objects.filter(pk=token.pk).update(last_used=timezone.now())

        user = token.user

        if not user.is_active:
            raise exceptions.AuthenticationFailed("User inactive")

        return user, token


class TokenPermissions(DjangoObjectPermissions):
    """
    Custom permissions handler which extends the built-in DjangoModelPermissions to validate a Token's write ability
    for unsafe requests (POST/PUT/PATCH/DELETE).
    """

    # Override the stock perm_map to enforce view permissions
    perms_map = {
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": [],
        "HEAD": ["%(app_label)s.view_%(model_name)s"],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }

    def __init__(self):

        # whether read-only access is provided to anonymous users.
        self.authenticated_users_only = True

        super().__init__()

    def _verify_write_permission(self, request):

        # If token authentication is in use, verify that the token allows write operations (for unsafe methods).
        if request.method in SAFE_METHODS or request.auth.write_enabled:
            return True
        return False

    def has_permission(self, request, view):

        # Enforce Token write ability
        if isinstance(request.auth, Token) and not self._verify_write_permission(request):
            return False

        return super().has_permission(request, view)

    def has_object_permission(self, request, view, obj):

        # Enforce Token write ability
        if isinstance(request.auth, Token) and not self._verify_write_permission(request):
            return False

        return super().has_object_permission(request, view, obj)


class TokenWritePermission(BasePermission):
    """
    Verify the token has write_enabled for unsafe methods, without requiring specific model permissions.
    Used for custom actions that accept user data but don't map to standard CRUD operations.
    """

    def has_permission(self, request, view):
        if not isinstance(request.auth, Token):
            raise exceptions.PermissionDenied("TokenWritePermission requires token authentication.")
        return bool(request.method in SAFE_METHODS or request.auth.write_enabled)


class TokenScheme(OpenApiAuthenticationExtension):
    target_class = "coldfront.api.authentication.TokenAuthentication"
    name = "tokenAuth"
    match_subclasses = True

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": "`Bearer <key>.<token>`",
        }
