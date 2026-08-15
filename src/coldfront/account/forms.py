# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from crispy_forms.layout import Layout
from django.contrib.auth.forms import PasswordChangeForm as _PasswordChangeForm

from coldfront.forms.mixins import HorizontalFormMixin


class PasswordChangeForm(HorizontalFormMixin, _PasswordChangeForm):
    fieldsets = (
        Layout(
            "old_password",
            "new_password1",
            "new_password2",
        ),
    )
