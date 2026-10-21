# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.contrib.auth.forms import PasswordChangeForm as _PasswordChangeForm

from coldfront.lib.forms.layout import FieldSet


class PasswordChangeForm(_PasswordChangeForm):
    fieldsets = (
        FieldSet(
            "old_password",
            "new_password1",
            "new_password2",
        ),
    )
