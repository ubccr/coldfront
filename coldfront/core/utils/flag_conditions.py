from coldfront.core.utils.common import display_time_zone_current_date
from django.core.exceptions import ValidationError
from flags import conditions


"""Conditions that dynamically enable flags in django-flags."""


def validate_during_month(month_number_str):
    if month_number_str not in [str(m + 1) for m in range(12)]:
        raise ValidationError('Enter a valid month between 1 and 12.')


@conditions.register('during month', validator=validate_during_month)
def during_month_condition(month_number_str, request=None, **kwargs):
    return int(month_number_str) == display_time_zone_current_date().month
