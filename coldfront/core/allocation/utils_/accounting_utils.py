from datetime import datetime
from decimal import Decimal

from django.conf import settings
from django.db import transaction

from coldfront.core.allocation.models import AllocationAttribute
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AllocationAttributeUsage
from coldfront.core.allocation.models import AllocationUserAttribute
from coldfront.core.allocation.models import AllocationUserAttributeUsage
from coldfront.core.project.models import ProjectUser
from coldfront.core.statistics.models import ProjectTransaction
from coldfront.core.statistics.models import ProjectUserTransaction
from coldfront.core.utils.common import assert_obj_type
from coldfront.core.utils.common import utc_now_offset_aware


def assert_attribute_type_is_service_units(attribute):
    """Raise an AssertionError if the type of the given
    AllocationAttribute or AllocationUserAttribute object does not have
    the name 'Service Units'."""
    actual_name = attribute.allocation_attribute_type.name
    expected_name = 'Service Units'
    message = (
        f'Attribute {attribute.pk} does not have allocation_attribute_type '
        f'{expected_name}.')
    assert actual_name == expected_name, message


def assert_num_service_units_in_bounds(num_service_units):
    """Given a Decimal representing a number of service units to assign,
    raise an AssertionError if it is not between the allowed minimum and
    maximum."""
    minimum, maximum = settings.ALLOCATION_MIN, settings.ALLOCATION_MAX
    message = (
        f'Number of service units {num_service_units} is not in the '
        f'acceptable bounds: [{minimum}, {maximum}].')
    assert minimum <= num_service_units <= maximum, message


def set_allocation_service_units_allowance(allocation_attribute,
                                           num_service_units,
                                           transaction_date_time=None,
                                           change_reason=None):
    """Set the number of Service Units for the given AllocationAttribute
    to the given amount. Create a ProjectTransaction at the current time
    or the given one. Optionally set a reason for the change in the
    created HistoricalAllocationAttribute.

    Note: The value of the attribute is stored as a string.

    Parameters:
        - allocation_attribute (AllocationAttribute)
        - num_service_units (Decimal)
        - transaction_date_time (datetime)
        - change_reason (str)

    Returns:
        - None

    Raises:
        - AssertionError
        - MultipleObjectsReturned
        - ObjectDoesNotExist
    """
    model = AllocationAttribute

    assert_obj_type(allocation_attribute, model)
    assert_attribute_type_is_service_units(allocation_attribute)
    assert_obj_type(num_service_units, Decimal)
    assert_obj_type(transaction_date_time, datetime, null_allowed=True)
    transaction_date_time = transaction_date_time or utc_now_offset_aware()
    assert_obj_type(change_reason, str, null_allowed=True)

    project = allocation_attribute.allocation.project

    with transaction.atomic():
        allocation_attribute = model.objects.select_for_update().get(
            pk=allocation_attribute.pk)
        allocation_attribute.value = str(num_service_units)
        allocation_attribute.save()
        allocation_attribute.refresh_from_db()

        ProjectTransaction.objects.create(
            project=project,
            date_time=transaction_date_time,
            allocation=num_service_units)

        if change_reason is not None:
            set_latest_history_change_reason(
                allocation_attribute, change_reason)

    return allocation_attribute


def set_allocation_service_units_usage(allocation_attribute_usage,
                                       num_service_units, change_reason=None):
    """Set the number of Service Units for the given
    AllocationAttributeUsage to the given amount. Optionally set a
    reason for the change in the created
    HistoricalAllocationAttributeUsage.

    Note: The value of the usage is stored as a Decimal.

    Parameters:
        - allocation_attribute_usage (AllocationAttributeUsage)
        - num_service_units (Decimal)
        - change_reason (str)

    Returns:
        - None

    Raises:
        - AssertionError
        - MultipleObjectsReturned
        - ObjectDoesNotExist
    """
    model = AllocationAttributeUsage

    assert_obj_type(allocation_attribute_usage, model)
    assert_attribute_type_is_service_units(
        allocation_attribute_usage.allocation_attribute)
    assert_obj_type(num_service_units, Decimal)
    assert_obj_type(change_reason, str, null_allowed=True)

    with transaction.atomic():
        allocation_attribute_usage = model.objects.select_for_update().get(
            pk=allocation_attribute_usage.pk)
        allocation_attribute_usage.value = num_service_units
        allocation_attribute_usage.save()
        allocation_attribute_usage.refresh_from_db()

        if change_reason is not None:
            set_latest_history_change_reason(
                allocation_attribute_usage, change_reason)


def set_allocation_user_service_units_allowance(allocation_user_attribute,
                                                num_service_units,
                                                transaction_date_time=None,
                                                change_reason=None):
    """Set the number of Service Units for the given
    AllocationUserAttribute to the given amount. Create a
    ProjectUserTransaction at the current time or the given one.
    Optionally set a reason for the change in the created
    HistoricalAllocationUserAttribute.

    Note: The value of the attribute is stored as a string.

    Parameters:
        - allocation_user_attribute (AllocationUserAttribute)
        - num_service_units (Decimal)
        - transaction_date_time (datetime)
        - change_reason (str)

    Returns:
        - None

    Raises:
        - AssertionError
        - MultipleObjectsReturned
        - ObjectDoesNotExist
    """
    model = AllocationUserAttribute

    assert_obj_type(allocation_user_attribute, model)
    assert_attribute_type_is_service_units(allocation_user_attribute)
    assert_obj_type(num_service_units, Decimal)
    assert_obj_type(transaction_date_time, datetime, null_allowed=True)
    transaction_date_time = transaction_date_time or utc_now_offset_aware()
    assert_obj_type(change_reason, str, null_allowed=True)

    # A ProjectUser may not exist for an AllocationUser who was removed from
    # the Project. Only add a transaction if one exists.
    try:
        project_user = ProjectUser.objects.get(
            project=allocation_user_attribute.allocation.project,
            user=allocation_user_attribute.allocation_user.user)
    except ProjectUser.DoesNotExist:
        project_user = None

    with transaction.atomic():
        allocation_user_attribute = model.objects.select_for_update().get(
            pk=allocation_user_attribute.pk)
        allocation_user_attribute.value = str(num_service_units)
        allocation_user_attribute.save()
        allocation_user_attribute.refresh_from_db()

        if project_user is not None:
            ProjectUserTransaction.objects.create(
                project_user=project_user,
                date_time=transaction_date_time,
                allocation=num_service_units)

        if change_reason is not None:
            set_latest_history_change_reason(
                allocation_user_attribute, change_reason)


def set_allocation_user_service_units_usage(allocation_user_attribute_usage,
                                            num_service_units,
                                            change_reason=None):
    """Set the number of Service Units for the given
    AllocationUserAttributeUsage to the given amount. Optionally set a
    reason for the change in the created
    HistoricalAllocationUserAttributeUsage.

    Note: The value of the usage is stored as a Decimal.

    Parameters:
        - allocation_user_attribute_usage (AllocationUserAttributeUsage)
        - num_service_units (Decimal)
        - change_reason (str)

    Returns:
        - None

    Raises:
        - AssertionError
        - MultipleObjectsReturned
        - ObjectDoesNotExist
    """
    model = AllocationUserAttributeUsage

    assert_obj_type(allocation_user_attribute_usage, model)
    assert_attribute_type_is_service_units(
        allocation_user_attribute_usage.allocation_user_attribute)
    assert_obj_type(num_service_units, Decimal)
    assert_obj_type(change_reason, str, null_allowed=True)

    with transaction.atomic():
        allocation_user_attribute_usage = \
            model.objects.select_for_update().get(
                pk=allocation_user_attribute_usage.pk)
        allocation_user_attribute_usage.value = num_service_units
        allocation_user_attribute_usage.save()
        allocation_user_attribute_usage.refresh_from_db()

        if change_reason is not None:
            set_latest_history_change_reason(
                allocation_user_attribute_usage, change_reason)


def set_latest_history_change_reason(instance, reason):
    """For the given model instance with a history, set the
    'history_change_reason' for the latest-created historical object to
    the given string."""
    historical_instances = instance.history.all()
    if historical_instances.exists():
        latest_historical_instance = historical_instances.latest('history_id')
        latest_historical_instance.history_change_reason = reason
        latest_historical_instance.save()


def set_service_units(accounting_allocation_objects, allocation_allowance=None,
                      allocation_usage=None,
                      allocation_transaction_date_time=None,
                      allocation_change_reason=None, user_allowance=None,
                      user_usage=None, user_transaction_date_time=None,
                      user_change_reason=None):
    """Set the Service Units for any, some, or all of the following: an
    Allocation's allowance, its usage, its AllocationUsers' allowances,
    or its AllocationUsers' usages. Create transactions at the current
    time or the given one as needed. Optionally set reasons for the
    changes in created historical objects.

    Note: A particular change reason is set for both the allowance and
    the usage.

    Parameters:
        - accounting_allocation_objects (AccountingAllocationObjects)
        - allocation_allowance (Decimal)
        - allocation_usage (Decimal)
        - allocation_transaction_date_time (datetime)
        - allocation_change_reason (str)
        - user_allowance (Decimal)
        - user_usage (Decimal)
        - user_transaction_date_time (datetime)
        - user_change_reason (str)

    Returns:
        - None

    Raises:
        - AssertionError
        - MultipleObjectsReturned
        - ObjectDoesNotExist
    """
    allocation_kwargs = {
        'allowance': allocation_allowance,
        'usage': allocation_usage,
        'transaction_date_time': allocation_transaction_date_time,
        'change_reason': allocation_change_reason,
    }
    allocation_user_kwargs = {
        'allowance': user_allowance,
        'usage': user_usage,
        'transaction_date_time': user_transaction_date_time,
        'change_reason': user_change_reason,
    }
    with transaction.atomic():
        set_service_units_for_allocation(
            accounting_allocation_objects, **allocation_kwargs)
        set_service_units_for_allocation_users(
            accounting_allocation_objects, **allocation_user_kwargs)


def set_service_units_for_allocation(accounting_allocation_objects,
                                     allowance=None, usage=None,
                                     transaction_date_time=None,
                                     change_reason=None):
    """Set the Service Units for either or both of the following: an
    Allocation's allowance or its usage. Create a ProjectTransaction at
    the current time or the given one. Optionally set a reason for the
    change in created historical objects.

    Note: The change reason is set for both the allowance and the usage.

    Parameters:
        - accounting_allocation_objects (AccountingAllocationObjects)
        - allowance (Decimal)
        - usage (Decimal)
        - transaction_date_time (datetime)
        - change_reason (str)

    Returns:
        - None

    Raises:
        - AssertionError
        - MultipleObjectsReturned
        - ObjectDoesNotExist
    """
    allocation_attribute = accounting_allocation_objects.allocation_attribute
    allocation_attribute_usage = \
        accounting_allocation_objects.allocation_attribute_usage

    set_allowance = allowance is not None
    set_usage = usage is not None

    if set_allowance:
        assert_num_service_units_in_bounds(allowance)
    if set_usage:
        assert_num_service_units_in_bounds(usage)

    with transaction.atomic():
        if set_allowance:
            set_allocation_service_units_allowance(
                allocation_attribute, allowance,
                transaction_date_time=transaction_date_time,
                change_reason=change_reason)
        if set_usage:
            set_allocation_service_units_usage(
                allocation_attribute_usage, usage, change_reason=change_reason)


def set_service_units_for_allocation_users(accounting_allocation_objects,
                                           allowance=None, usage=None,
                                           transaction_date_time=None,
                                           change_reason=None):
    """Set the Service Units for either or both of the following, an
    Allocation's AllocationUsers' allowances or their usages. Create
    ProjectUserTransactions at the current time or the given one.
    Optionally set a reason for the change in created historical
    objects.

    Note: The change reason is set for both the allowances and the
    usages for all users.

    Parameters:
        - accounting_allocation_objects (AccountingAllocationObjects)
        - allowance (Decimal)
        - usage (Decimal)
        - transaction_date_time (datetime)
        - change_reason (str)

    Returns:
        - None

    Raises:
        - AssertionError
        - MultipleObjectsReturned
        - ObjectDoesNotExist
    """
    allocation = accounting_allocation_objects.allocation

    set_allowance = allowance is not None
    set_usage = usage is not None

    if set_allowance:
        assert_num_service_units_in_bounds(allowance)
    if set_usage:
        assert_num_service_units_in_bounds(usage)

    service_units_type = AllocationAttributeType.objects.get(
        name='Service Units')
    service_units_user_attributes = \
        allocation.allocationuserattribute_set.filter(
            allocation_attribute_type=service_units_type)

    with transaction.atomic():
        for allocation_user_attribute in service_units_user_attributes:
            if set_allowance:
                set_allocation_user_service_units_allowance(
                    allocation_user_attribute, allowance,
                    transaction_date_time=transaction_date_time,
                    change_reason=change_reason)
            if set_usage:
                allocation_user_attribute_usage = \
                    allocation_user_attribute.allocationuserattributeusage
                set_allocation_user_service_units_usage(
                    allocation_user_attribute_usage, usage,
                    change_reason=change_reason)
