# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied

from coldfront.api.serializers import ValidatedModelSerializer
from coldfront.users.models import Token

from .users import UserSerializer

__all__ = (
    "TokenProvisionSerializer",
    "TokenSerializer",
)


class TokenSerializer(ValidatedModelSerializer):
    token = serializers.CharField(
        required=False,
        default=Token.generate,
    )
    user = UserSerializer(nested=True)

    class Meta:
        model = Token
        fields = (
            "id",
            "url",
            "display_url",
            "display",
            "key",
            "user",
            "description",
            "created",
            "expires",
            "last_used",
            "enabled",
            "write_enabled",
            "pepper_id",
            "token",
        )
        read_only_fields = ("key",)
        brief_fields = ("id", "url", "display", "key", "enabled", "write_enabled", "description")

    def get_fields(self):
        fields = super().get_fields()

        # Make user field read-only if updating an existing Token.
        if self.instance is not None:
            fields["user"].read_only = True

        return fields

    def validate(self, data):

        # If the Token is being created on behalf of another user, enforce the grant_token permission.
        request = self.context.get("request")
        token_user = data.get("user")
        if token_user and token_user != request.user and not request.user.has_perm("users.grant_token"):
            raise PermissionDenied("This user does not have permission to create tokens for other users.")

        return super().validate(data)


class TokenProvisionSerializer(TokenSerializer):
    user = UserSerializer(nested=True, read_only=True)
    username = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)
    last_used = serializers.DateTimeField(read_only=True)
    key = serializers.CharField(read_only=True)

    class Meta:
        model = Token
        fields = (
            "id",
            "url",
            "display_url",
            "display",
            "user",
            "key",
            "created",
            "expires",
            "last_used",
            "key",
            "enabled",
            "write_enabled",
            "description",
            "username",
            "password",
            "token",
        )

    def validate(self, data):
        # Validate the username and password
        username = data.pop("username")
        password = data.pop("password")
        user = authenticate(request=self.context.get("request"), username=username, password=password)
        if user is None:
            raise AuthenticationFailed("Invalid username/password")

        # Inject the user into the validated data
        data["user"] = user

        return data
