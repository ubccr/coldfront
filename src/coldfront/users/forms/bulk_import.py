# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django import forms
from django.utils.translation import gettext as _

from coldfront.forms import CSVModelForm
from coldfront.users.models import Group, Role, Token, User

__all__ = (
    "GroupImportForm",
    "TokenImportForm",
    "UserImportForm",
)


class GroupImportForm(CSVModelForm):
    class Meta:
        model = Group
        fields = ("name", "description")


class UserImportForm(CSVModelForm):
    password = forms.CharField(
        label=_("Password"),
        required=False,
        help_text=_("If no password is provided, the password will be set to unusable."),
    )

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "password", "is_active", "is_superuser")

    def save(self, *args, **kwargs):
        # Set the hashed password or set unusable if not set
        password = self.cleaned_data.get("password")
        if password:
            self.instance.set_password(self.cleaned_data.get("password"))
        else:
            self.instance.set_unusable_password()

        return super().save(*args, **kwargs)


class RoleImportForm(CSVModelForm):
    class Meta:
        model = Role
        fields = ("name", "description", "weight")


class TokenImportForm(CSVModelForm):
    token = forms.CharField(
        label=_("Token"),
        required=False,
        help_text=_("If no token is provided, one will be generated automatically."),
    )

    class Meta:
        model = Token
        fields = (
            "user",
            "token",
            "enabled",
            "write_enabled",
            "expires",
            "description",
        )
