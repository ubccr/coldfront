from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationAttribute
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AllocationAttributeUsage
from coldfront.core.allocation.models import AllocationStatusChoice
from coldfront.core.allocation.models import AllocationUser
from coldfront.core.allocation.models import AllocationUserAttribute
from coldfront.core.allocation.models import AllocationUserAttributeUsage
from coldfront.core.allocation.models import AllocationUserStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserStatusChoice
from collections import namedtuple
from datetime import datetime
from datetime import timedelta
from django.conf import settings


AccountingAllocationObjects = namedtuple(
    'AccountingAllocationObjects', (
        'allocation '
        'allocation_user '
        'allocation_attribute '
        'allocation_attribute_usage '
        'allocation_user_attribute '
        'allocation_user_attribute_usage'))


def convert_datetime_to_unix_timestamp(dt):
    """Returns the given datetime object as the number of seconds since
    the beginning of the epoch.

    Parameters:
        - dt (datetime): the datetime object to convert

    Returns:
        - int

    Raises:
        - TypeError, if the input is not a datetime object
    """
    if not isinstance(dt, datetime):
        raise TypeError(f'Datetime {dt} is not a datetime.')
    return (dt - datetime(1970, 1, 1)).total_seconds()


def get_accounting_allocation_objects(user, project):
    """Return a namedtuple of database objects related to accounting and
    allocation for the given user and project.

    Parameters:
        - user (User): an instance of the User model
        - project (Project): an instance of the Project model

    Returns:
        - namedtuple with name AccountingAllocationObjects

    Raises:
        - MultipleObjectsReturned, if a database retrieval returns more
        than one object
        - ObjectDoesNotExist, if a database retrieval returns less than
        one object
    """
    # Check that there is an active association between the user and project.
    active_status = ProjectUserStatusChoice.objects.get(name='Active')
    ProjectUser.objects.get(user=user, project=project, status=active_status)
    # Check that the project has an active allocation for the compute resource.
    active_status = AllocationStatusChoice.objects.get(name='Active')
    allocation = Allocation.objects.get(
        project=project, status=active_status, resources__name='Savio Compute')
    # Check that the user is an active member of the allocation.
    active_status = AllocationUserStatusChoice.objects.get(name='Active')
    allocation_user = AllocationUser.objects.get(
        allocation=allocation, user=user, status=active_status)
    # Check that the allocation has an attribute for Service Units and
    # an associated usage.
    allocation_attribute_type = AllocationAttributeType.objects.get(
        name='Service Units')
    allocation_attribute = AllocationAttribute.objects.get(
        allocation_attribute_type=allocation_attribute_type,
        allocation=allocation)
    AllocationAttributeUsage.objects.get(
        allocation_attribute=allocation_attribute)
    # Check that the allocation user has an attribute for Service Units
    # and an associated usage.
    allocation_user_attribute = AllocationUserAttribute.objects.get(
        allocation_attribute_type=allocation_attribute_type,
        allocation=allocation, allocation_user=allocation_user)
    AllocationUserAttributeUsage.objects.get(
        allocation_user_attribute=allocation_user_attribute)


def get_allocation_year_range():
    """Returns a pair of datetime objects corresponding to the start and
    end times, inclusive, of the current allocation year. The method may
    fail if the starting date is February 29th.

    Parameters:
        - None

    Returns:
        - Pair of datetime objects

    Raises:
        - TypeError, if settings variables are not integers
        - ValueError, if settings variables represent an invalid date
    """
    # Validate the types of the starting month and day, provided in the
    # settings.
    start_month = settings.ALLOCATION_YEAR_START_MONTH
    start_day = settings.ALLOCATION_YEAR_START_DAY
    if not isinstance(start_month, int):
        raise TypeError(f'Starting month {start_month} is not an integer.')
    if not isinstance(start_day, int):
        raise TypeError(f'Starting day {start_day} is not an integer.')
    # Run the calculation in a loop in case midnight is crossed, which may
    # change the result.
    while True:
        now = datetime.now()
        start_date_this_year = datetime(now.year, start_month, start_day)
        if now < start_date_this_year:
            # The start date has not occurred yet this year.
            # The period began last year and will end this year.
            start = start_date_this_year.replace(
                year=start_date_this_year.year - 1)
            end = start_date_this_year - timedelta(microseconds=1)
        else:
            # The start date has already occurred this year.
            # The period began this year and will end next year.
            start = start_date_this_year
            end = (start.replace(year=start.year + 1) -
                   timedelta(microseconds=1))
        # Check that the day did not change during calculation.
        if datetime.now().day == now.day:
            # The result is stable, so break and return.
            break
    return start, end
