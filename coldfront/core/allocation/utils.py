import os
from datetime import datetime
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import BooleanField
from django.db.models import Case
from django.db.models import Q
from django.db.models import Value
from django.db.models import When
from django.urls import reverse
from urllib.parse import urljoin

from coldfront.core.allocation.models import (AllocationAttributeType,
                                              AllocationPeriod,
                                              AllocationUser,
                                              AllocationUserAttribute,
                                              AllocationUserStatusChoice,
                                              Allocation,
                                              AllocationStatusChoice,
                                              AllocationAttribute,
                                              SecureDirAddUserRequest,
                                              SecureDirAddUserRequestStatusChoice,
                                              SecureDirRemoveUserRequest,
                                              SecureDirRemoveUserRequestStatusChoice,
                                              SecureDirRequest,
                                              SecureDirRequestStatusChoice)
from coldfront.core.allocation.signals import allocation_activate_user
from coldfront.core.project.models import Project
from coldfront.core.resource.models import Resource
from coldfront.core.resource.utils import get_primary_compute_resource_name
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.utils.common import display_time_zone_current_date
from coldfront.core.utils.common import utc_now_offset_aware

from flags.state import flag_enabled

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
            (Q(is_public=True) |
             Q(allowed_groups__in=user_obj.groups.all()) |
             Q(allowed_users__in=[user_obj]))
        ).distinct()

    return resources


def test_allocation_function(allocation_pk):
    pass
    # print('test_allocation_function', allocation_pk)


def annotate_queryset_with_allocation_period_not_started_bool(queryset):
    """Given a queryset of instances that may have an AllocationPeriod,
    annotate each instance with a boolean field named
    'allocation_period_not_started', which is True if it (a) has an
    AllocationPeriod and (b) that period has not started."""
    date = display_time_zone_current_date()
    return queryset.annotate(
        allocation_period_not_started=Case(
            When(
                Q(allocation_period__isnull=False) &
                Q(allocation_period__start_date__gt=date),
                then=Value(True)),
            default=Value(False),
            output_field=BooleanField()))


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


def get_project_compute_resource_name(project_obj):
    """Return the name of the '{cluster_name} Compute' Resource that
    corresponds to the given Project.

    The name is based on currently-enabled flags (i.e., BRC, LRC). If
    one cannot be determined, return the empty string."""
    if flag_enabled('BRC_ONLY'):
        if project_obj.name == 'abc':
            resource_name = 'ABC Compute'
        elif project_obj.name.startswith('vector_'):
            resource_name = 'Vector Compute'
        else:
            resource_name = get_primary_compute_resource_name()
        return resource_name
    if flag_enabled('LRC_ONLY'):
        computing_allowance_interface = ComputingAllowanceInterface()
        project_name_prefixes = tuple([
            computing_allowance_interface.code_from_name(allowance.name)
            for allowance in computing_allowance_interface.allowances()])
        if project_obj.name.startswith(project_name_prefixes):
            resource_name = get_primary_compute_resource_name()
        else:
            # TODO: Verify this behavior.
            resource_name = f'{project_obj.name.upper()} Compute'
        return resource_name
    return ''


def get_project_compute_allocation(project_obj):
    """Return the given Project's Allocation to a
    '{cluster_name} Compute' Resource."""
    resource_name = get_project_compute_resource_name(project_obj)
    return project_obj.allocation_set.get(resources__name=resource_name)


def prorated_allocation_amount(amount, dt, allocation_period):
    """Given a number of service units and a datetime, return the
    prorated number of service units that would be allocated in the
    given AllocationPeriod, based on the datetime's position within that
    period. If it is before, return the full amount. If it is after,
    return zero.

    Parameters:
        - amount (Decimal): a base number of service units.
        - dt (datetime): a datetime object whose month is used in the
                         calculation, based on its position relative to
                         the start month of the given AllocationPeriod.
        - allocation_period (AllocationPeriod): an AllocationPeriod
                                                object to compare the
                                                datetime against.

    Returns:
        - Decimal

    Raises:
        - TypeError, if any argument has an invalid type
        - ValueError, if the provided amount is outside the allowed
        range for allocations
    """
    if not isinstance(amount, Decimal):
        raise TypeError(f'Invalid Decimal {amount}.')
    if not isinstance(dt, datetime):
        raise TypeError(f'Invalid datetime {dt}.')
    if not isinstance(allocation_period, AllocationPeriod):
        raise TypeError(f'Invalid AllocationPeriod {allocation_period}.')
    if not (settings.ALLOCATION_MIN < amount < settings.ALLOCATION_MAX):
        raise ValueError(f'Invalid amount {amount}.')
    date = dt.astimezone(pytz.timezone(settings.DISPLAY_TIME_ZONE)).date()
    start, end = allocation_period.start_date, allocation_period.end_date
    if date < start:
        return amount
    if date > end:
        return settings.ALLOCATION_MIN
    month = date.month
    amount_per_month = amount / 12
    start_month = start.month
    if month >= start_month:
        amount = amount - amount_per_month * (month - start_month)
    else:
        amount = amount_per_month * (start_month - month)
    return Decimal(f'{math.floor(amount):.2f}')


def review_cluster_access_requests_url():
    domain = settings.CENTER_BASE_URL
    view = reverse('allocation-cluster-account-request-list')
    return urljoin(domain, view)


def create_secure_dirs(project, subdirectory_name, scratch_or_groups):
    """
    Creates one secure directory allocation: either a group directory or a
    scratch directory, depending on scratch_or_groups. Additionally creates
    an AllocationAttribute for the new allocation that corresponds to the
    directory path on the cluster.
    Parameters:
        - project (Project): a Project object to create a secure directory
                            allocation for
        - subdirectory_name (str): the name of the subdirectory on the cluster
        - scratch_or_groups (str): one of either 'scratch' or 'groups'
    Returns:
        - allocation
    Raises:
        - TypeError, if subdirectory_name has an invalid type
        - ValueError, if scratch_or_groups does not have a valid value
        - ValidationError, if the Allocations already exist
    """

    if not isinstance(project, Project):
        raise TypeError(f'Invalid Project {project}.')
    if not isinstance(subdirectory_name, str):
        raise TypeError(f'Invalid subdirectory_name {subdirectory_name}.')
    if scratch_or_groups not in ['scratch', 'groups']:
        raise ValueError(f'Invalid scratch_or_groups arg {scratch_or_groups}.')

    if scratch_or_groups == 'scratch':
        p2p3_directory = Resource.objects.get(name='Scratch P2/P3 Directory')
    else:
        p2p3_directory = Resource.objects.get(name='Groups P2/P3 Directory')

    query = Allocation.objects.filter(project=project,
                                      resources__in=[p2p3_directory])

    if query.exists():
        raise ValidationError('Allocation already exist')

    allocation = Allocation.objects.create(
        project=project,
        status=AllocationStatusChoice.objects.get(name='Active'),
        start_date=utc_now_offset_aware())

    p2p3_path = p2p3_directory.resourceattribute_set.get(
        resource_attribute_type__name='path')

    allocation.resources.add(p2p3_directory)

    allocation_attribute_type = AllocationAttributeType.objects.get(
        name='Cluster Directory Access')

    p2p3_subdirectory = AllocationAttribute.objects.create(
        allocation_attribute_type=allocation_attribute_type,
        allocation=allocation,
        value=os.path.join(p2p3_path.value, subdirectory_name))

    return allocation


def get_secure_dir_manage_user_request_objects(self, action):
    """
    Sets attributes pertaining to a secure directory based on the
    action being performed.
    Parameters:
        - self (object): object to set attributes for
        - action (str): the action being performed, either 'add' or 'remove'
    Raises:
        - TypeError, if the 'self' object is not an object
        - ValueError, if action is not one of 'add' or 'remove'
    """

    action = action.lower()
    if not isinstance(self, object):
        raise TypeError(f'Invalid self {self}.')
    if action not in ['add', 'remove']:
        raise ValueError(f'Invalid action {action}.')

    add_bool = action == 'add'

    request_obj = SecureDirAddUserRequest \
        if add_bool else SecureDirRemoveUserRequest
    request_status_obj = SecureDirAddUserRequestStatusChoice \
        if add_bool else SecureDirRemoveUserRequestStatusChoice

    language_dict = {
        'preposition': 'to' if add_bool else 'from',
        'noun': 'addition' if add_bool else 'removal',
        'verb': 'add' if add_bool else 'remove'
    }

    setattr(self, 'action', action.lower())
    setattr(self, 'add_bool', add_bool)
    setattr(self, 'request_obj', request_obj)
    setattr(self, 'request_status_obj', request_status_obj)
    setattr(self, 'language_dict', language_dict)


def has_cluster_access(user):
    """
    Returns True if the user has cluster access, False otherwise
    Parameters:
    - user (User): the user to check
    Raises:
    - TypeError, if user is not a User object
    Returns:
    - Bool: True if the user has cluster access and False otherwise
    """
    if not isinstance(user, User):
        raise TypeError(f'Invalid User {user}.')

    return AllocationUserAttribute.objects.filter(
        allocation_user__user=user,
        allocation_attribute_type__name='Cluster Account Status',
        value='Active').exists()
