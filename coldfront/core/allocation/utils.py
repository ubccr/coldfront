from datetime import datetime
from decimal import Decimal

from django.conf import settings
from django.db.models import Q
from django.urls import reverse
from urllib.parse import urljoin

from coldfront.core.allocation.models import (AllocationAttributeType,
                                              AllocationUser,
                                              AllocationUserAttribute,
                                              AllocationUserStatusChoice)
from coldfront.core.allocation.signals import allocation_activate_user
from coldfront.core.resource.models import Resource
from coldfront.core.utils.common import utc_now_offset_aware

import math
import pytz


def set_allocation_user_status_to_error(allocation_user_pk):
    allocation_user_obj = AllocationUser.objects.get(pk=allocation_user_pk)
    error_status = AllocationUserStatusChoice.objects.get(name='Error')
    allocation_user_obj.status = error_status
    allocation_user_obj.save()


def generate_guauge_data_from_usage(name, value, usage):

    label = "%s: %.2f of %.2f" % (name, usage, value)

    try:
        percent = (usage/value)*100
    except ZeroDivisionError:
        percent = 0

    if percent < 80:
        color = "#6da04b"
    elif percent >= 80 and percent < 90:
        color = "#ffc72c"
    else:
        color = "#e56a54"

    usage_data = {
        "columns": [
            [label, percent],
        ],
        "type": 'gauge',
        "colors": {
            label: color
        }
    }

    return usage_data


def get_user_resources(user_obj):

    if user_obj.is_superuser:
        resources = Resource.objects.filter(is_allocatable=True)
    else:
        resources = Resource.objects.filter(
            Q(is_allocatable=True) &
            Q(is_available=True) &
            (Q(is_public=True) | Q(allowed_groups__in=user_obj.groups.all()) | Q(allowed_users__in=[user_obj,]))
        ).distinct()

    return resources


def test_allocation_function(allocation_pk):
    pass
    # print('test_allocation_function', allocation_pk)


def get_or_create_active_allocation_user(allocation_obj, user_obj):
    allocation_user_status_choice = \
        AllocationUserStatusChoice.objects.get(name='Active')
    if allocation_obj.allocationuser_set.filter(user=user_obj).exists():
        allocation_user_obj = allocation_obj.allocationuser_set.get(
            user=user_obj)
        allocation_user_obj.status = allocation_user_status_choice
        allocation_user_obj.save()
    else:
        allocation_user_obj = AllocationUser.objects.create(
            allocation=allocation_obj, user=user_obj,
            status=allocation_user_status_choice)
    allocation_activate_user.send(
        sender=None, allocation_user_pk=allocation_user_obj.pk)
    return allocation_user_obj


def set_allocation_user_attribute_value(allocation_user_obj, type_name, value):
    allocation_attribute_type = AllocationAttributeType.objects.get(
        name=type_name)
    allocation_user_attribute, _ = \
        AllocationUserAttribute.objects.get_or_create(
            allocation_attribute_type=allocation_attribute_type,
            allocation=allocation_user_obj.allocation,
            allocation_user=allocation_user_obj)
    allocation_user_attribute.value = value
    allocation_user_attribute.save()
    return allocation_user_attribute


def get_allocation_user_cluster_access_status(allocation_obj, user_obj):
    return allocation_obj.allocationuserattribute_set.get(
        allocation_user__user=user_obj,
        allocation_attribute_type__name='Cluster Account Status',
        value__in=['Pending - Add', 'Processing', 'Active'])


def next_allocation_start_datetime():
    """Return a timezone-aware datetime object representing the start of
    the next allocation year.

    Parameters:
        - None

    Returns:
        - datetime
    """
    start_month = settings.ALLOCATION_YEAR_START_MONTH
    start_day = settings.ALLOCATION_YEAR_START_DAY
    local_tz = pytz.timezone('America/Los_Angeles')
    dt = utc_now_offset_aware().astimezone(local_tz)
    start_year = dt.year + int(dt.month >= start_month)
    return datetime(
        start_year, start_month, start_day, tzinfo=local_tz).astimezone(
            pytz.timezone(settings.TIME_ZONE))


def prorated_allocation_amount(amount, dt):
    """Given a number of service units and a datetime, return the
    prorated number of service units that would be allocated in the
    current allocation year, based on the datetime's month.

    Parameters:
        - amount (Decimal): a number of service units (e.g.,
                            settings.FCA_DEFAULT_ALLOCATION).
        - dt (datetime): a datetime object whose month is used in the
                         calculation, based on its position relative to
                         the start month of the allocation year.

    Returns:
        - Decimal

    Raises:
        - TypeError, if either argument has an invalid type
        - ValueError, if the provided amount is outside of the allowed
        range for allocations
    """
    if not isinstance(amount, Decimal):
        raise TypeError(f'Invalid Decimal {amount}.')
    if not isinstance(dt, datetime):
        raise TypeError(f'Invalid datetime {dt}.')
    if not (settings.ALLOCATION_MIN < amount < settings.ALLOCATION_MAX):
        raise ValueError(f'Invalid amount {amount}.')
    month = dt.month
    amount_per_month = amount / 12
    start_month = settings.ALLOCATION_YEAR_START_MONTH
    if month >= start_month:
        amount = amount - amount_per_month * (month - start_month)
    else:
        amount = amount_per_month * (start_month - month)
    return Decimal(f'{math.floor(amount):.2f}')


def review_cluster_access_requests_url():
    domain = settings.CENTER_BASE_URL
    view = reverse('allocation-cluster-account-request-list')
    return urljoin(domain, view)
