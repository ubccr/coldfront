# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import decimal
import re

from django.core.exceptions import ValidationError
from django.core.validators import BaseValidator, RegexValidator
from django.utils.translation import gettext_lazy as _

__all__ = ("ColorValidator",)


ColorValidator = RegexValidator(
    regex="^[0-9a-f]{6}$", message="Enter a valid hexadecimal RGB color code.", code="invalid"
)


def validate_regex(value):
    """
    Checks that the value is a valid regular expression. (Don't confuse this with RegexValidator, which *uses* a regex
    to validate a value.)
    """
    try:
        re.compile(value)
    except re.error:
        raise ValidationError(_("{value} is not a valid regular expression.").format(value=value))


class MultipleOfValidator(BaseValidator):
    """
    Checks that a field's value is a numeric multiple of the given value. Both values are
    cast as Decimals for comparison.
    """

    def __init__(self, multiple):
        self.multiple = decimal.Decimal(str(multiple))
        super().__init__(limit_value=None)

    def __call__(self, value):
        if decimal.Decimal(str(value)) % self.multiple != 0:
            raise ValidationError(
                _("{value} must be a multiple of {multiple}.").format(value=value, multiple=self.multiple)
            )
