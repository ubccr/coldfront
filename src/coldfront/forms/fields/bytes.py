# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import humanize
from django import forms
from django.core.exceptions import ValidationError

from coldfront.utils.bytes import InvalidSize, parse_bytes


class BytesField(forms.CharField):
    """
    A form field that accepts a human-readable byte size string (e.g. "10 TB")
    and converts it to an integer byte count for storage.

    Also accepts plain integer strings and empty/None values for nullable fields.
    """

    def prepare_value(self, value):
        if value in self.empty_values:
            return ""
        return humanize.naturalsize(value)

    def clean(self, value):
        value = super().clean(value)
        if value in (None, "", self.initial):
            return value if self.required else None
        try:
            return parse_bytes(value)
        except InvalidSize as exc:
            raise ValidationError(str(exc)) from exc
