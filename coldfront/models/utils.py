# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.conf import settings
from djmoney.money import Money
from shortuuid import ShortUUID


def auto_generate_slug(model_instance=None):
    """Auto generate a slug. This is the default implementation which generates a shortuuid of length 7 form a numeric alphabet"""

    from coldfront.ras.models import Allocation, Project

    prefix = "cf"

    if model_instance is not None:
        if issubclass(model_instance.__class__, Project):
            prefix = "p"
        elif issubclass(model_instance.__class__, Allocation):
            prefix = "a"

    return prefix + ShortUUID(alphabet="0123456789").random(length=7)


def get_default_currency():
    """Default currency used for MoneyFields"""
    return settings.DEFAULT_CURRENCY


def get_currency_choices():
    """Default currency choices for MoneyFields"""
    return settings.DEFAULT_CURRENCY_CHOICES


def get_default_zero():
    return Money("0.00", settings.DEFAULT_CURRENCY)
