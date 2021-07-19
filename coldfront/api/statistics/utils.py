from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationAttribute
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AllocationAttributeUsage
from coldfront.core.allocation.models import AllocationStatusChoice
from coldfront.core.allocation.models import AllocationUser
from coldfront.core.allocation.models import AllocationUserAttribute
from coldfront.core.allocation.models import AllocationUserAttributeUsage
from coldfront.core.allocation.models import AllocationUserStatusChoice
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.resource.models import Resource
from coldfront.core.statistics.models import ProjectTransaction
from coldfront.core.statistics.models import ProjectUserTransaction
from coldfront.core.utils.common import utc_now_offset_aware
from datetime import datetime
from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.contrib.auth.models import User
import logging


class AccountingAllocationObjects(object):
    """A container for related Allocation objects needed for
    accounting."""

    def __init__(self, allocation=None, allocation_user=None,
                 allocation_attribute=None, allocation_attribute_usage=None,
                 allocation_user_attribute=None,
                 allocation_user_attribute_usage=None):
        self.allocation = allocation
        self.allocation_user = allocation_user
        self.allocation_attribute = allocation_attribute
        self.allocation_attribute_usage = allocation_attribute_usage
        self.allocation_user_attribute = allocation_user_attribute
        self.allocation_user_attribute_usage = allocation_user_attribute_usage


def convert_datetime_to_unix_timestamp(dt):
    """Return the given datetime object as the number of seconds since
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


def create_project_allocation(project, value):
    """Create a compute allocation with the given value for the given
    Project; return the created objects.

    Parameters:
        - project (Project): an instance of the Project model
        - value (Decimal): the allocation value to be set

    Returns:
        - AccountingAllocationObjects with a subset of fields set

    Raises:
        - IntegrityError, if a database creation fails due to
        constraints
        - MultipleObjectsReturned, if a database retrieval returns more
        than one object
        - ObjectDoesNotExist, if a database retrieval returns less than
        one object
        - TypeError, if one or more inputs has the wrong type
    """
    if not isinstance(project, Project):
        raise TypeError(f'Project {project} is not a Project object.')
    if not isinstance(value, Decimal):
        raise TypeError(f'Value {value} is not a Decimal.')

    resource = Resource.objects.get(name='Savio Compute')

    status = AllocationStatusChoice.objects.get(name='Active')
    allocation = Allocation.objects.create(project=project, status=status)
    allocation.resources.add(resource)
    allocation.save()

    allocation_attribute_type = AllocationAttributeType.objects.get(
        name='Service Units')
    allocation_attribute = AllocationAttribute.objects.create(
        allocation_attribute_type=allocation_attribute_type,
        allocation=allocation, value=str(value))

    # Create a ProjectTransaction to store the change in service units.
    ProjectTransaction.objects.create(
        project=project,
        date_time=utc_now_offset_aware(),
        allocation=value)

    return AccountingAllocationObjects(
        allocation=allocation,
        allocation_attribute=allocation_attribute)


def create_user_project_allocation(user, project, value):
    """Create a compute allocation with the given value for the given
    User and Project; return the created objects.

    Parameters:
        - user (User): an instance of the User model
        - project (Project): an instance of the Project model
        - value (Decimal): the allocation value to be set

    Returns:
        - AccountingAllocationObjects with a subset of fields set

    Raises:
        - IntegrityError, if a database creation fails due to
        constraints
        - MultipleObjectsReturned, if a database retrieval returns more
        than one object
        - ObjectDoesNotExist, if a database retrieval returns less than
        one object
        - TypeError, if one or more inputs has the wrong type
    """
    if not isinstance(user, User):
        raise TypeError(f'User {user} is not a User object.')
    if not isinstance(project, Project):
        raise TypeError(f'Project {project} is not a Project object.')
    if not isinstance(value, Decimal):
        raise TypeError(f'Value {value} is not a Decimal.')

    resource = Resource.objects.get(name='Savio Compute')

    status = AllocationStatusChoice.objects.get(name='Active')
    allocation = Allocation.objects.get(
        project=project, status=status, resources__name=resource.name)

    status = AllocationUserStatusChoice.objects.get(name='Active')
    allocation_user = AllocationUser.objects.create(
        allocation=allocation, user=user, status=status)

    allocation_attribute_type = AllocationAttributeType.objects.get(
        name='Service Units')
    allocation_user_attribute = AllocationUserAttribute.objects.create(
        allocation_attribute_type=allocation_attribute_type,
        allocation=allocation, allocation_user=allocation_user,
        value=str(value))

    # Create a ProjectUserTransaction to store the change in service units.
    project_user = ProjectUser.objects.get(project=project, user=user)
    ProjectUserTransaction.objects.create(
        project_user=project_user,
        date_time=utc_now_offset_aware(),
        allocation=value)

    return AccountingAllocationObjects(
        allocation=allocation,
        allocation_user=allocation_user,
        allocation_user_attribute=allocation_user_attribute)


def get_accounting_allocation_objects(project, user=None):
    """Return a namedtuple of database objects related to accounting and
    allocation for the given project and optional user.

    Parameters:
        - project (Project): an instance of the Project model
        - user (User): an instance of the User model

    Returns:
        - AccountingAllocationObjects instance

    Raises:
        - MultipleObjectsReturned, if a database retrieval returns more
        than one object
        - ObjectDoesNotExist, if a database retrieval returns less than
        one object
        - TypeError, if one or more inputs has the wrong type
    """
    if not isinstance(project, Project):
        raise TypeError(f'Project {project} is not a Project object.')

    objects = AccountingAllocationObjects()

    # Check that the project has an active allocation for the compute resource.
    active_status = AllocationStatusChoice.objects.get(name='Active')

    allocation = Allocation.objects.get(
        project=project, status=active_status, resources__name='Savio Compute')

    # Check that the allocation has an attribute for Service Units and
    # an associated usage.
    allocation_attribute_type = AllocationAttributeType.objects.get(
        name='Service Units')
    allocation_attribute = AllocationAttribute.objects.get(
        allocation_attribute_type=allocation_attribute_type,
        allocation=allocation)
    allocation_attribute_usage = AllocationAttributeUsage.objects.get(
        allocation_attribute=allocation_attribute)

    objects.allocation = allocation
    objects.allocation_attribute = allocation_attribute
    objects.allocation_attribute_usage = allocation_attribute_usage

    if user is None:
        return objects

    if not isinstance(user, User):
        raise TypeError(f'User {user} is not a User object.')

    # Check that there is an active association between the user and project.
    active_status = ProjectUserStatusChoice.objects.get(name='Active')
    ProjectUser.objects.get(user=user, project=project, status=active_status)

    # Check that the user is an active member of the allocation.
    active_status = AllocationUserStatusChoice.objects.get(name='Active')
    allocation_user = AllocationUser.objects.get(
        allocation=allocation, user=user, status=active_status)

    # Check that the allocation user has an attribute for Service Units
    # and an associated usage.
    allocation_user_attribute = AllocationUserAttribute.objects.get(
        allocation_attribute_type=allocation_attribute_type,
        allocation=allocation, allocation_user=allocation_user)
    allocation_user_attribute_usage = AllocationUserAttributeUsage.objects.get(
        allocation_user_attribute=allocation_user_attribute)

    objects.allocation_user = allocation_user
    objects.allocation_user_attribute = allocation_user_attribute
    objects.allocation_user_attribute_usage = allocation_user_attribute_usage

    return objects


def get_allocation_year_range():
    """Return a pair of datetime objects corresponding to the start and
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


def set_project_allocation_value(project, value):
    """Set the value of the compute allocation for the given Project;
    return whether or not the update was performed successfully.

    Parameters:
        - project (Project): an instance of the Project model
        - value (Decimal): the allocation value to be set

    Returns:
        - Boolean denoting success or failure

    Raises:
        - TypeError, if one or more inputs has the wrong type
    """
    if not isinstance(project, Project):
        raise TypeError(f'Project {project} is not a Project object.')
    if not isinstance(value, Decimal):
        raise TypeError(f'Value {value} is not a Decimal.')
    try:
        allocation_objects = get_accounting_allocation_objects(project)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(e)
        return False
    project_allocation = allocation_objects.allocation_attribute
    project_allocation.value = str(value)
    project_allocation.save()
    return True


def set_project_usage_value(project, value):
    """Set the value of the usage for the compute allocation for the
    given Project; return whether or not the update was performed
    successfully.

    Parameters:
        - project (Project): an instance of the Project model
        - value (Decimal): the allocation value to be set

    Returns:
        - Boolean denoting success or failure

    Raises:
        - TypeError, if one or more inputs has the wrong type
    """
    if not isinstance(project, Project):
        raise TypeError(f'Project {project} is not a Project object.')
    if not isinstance(value, Decimal):
        raise TypeError(f'Value {value} is not a Decimal.')
    try:
        allocation_objects = get_accounting_allocation_objects(project)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(e)
        return False
    project_usage = allocation_objects.allocation_attribute_usage
    project_usage.value = value
    project_usage.save()
    return True


def set_user_project_allocation_value(user, project, value):
    """Set the value of the compute allocation for the given User and
    Project; return whether or not the update was performed
    successfully.

    Parameters:
        - user (User): an instance of the User model
        - project (Project): an instance of the Project model
        - value (Decimal): the allocation value to be set

    Returns:
        - Boolean denoting success or failure

    Raises:
        - TypeError, if one or more inputs has the wrong type
    """
    if not isinstance(user, User):
        raise TypeError(f'User {user} is not a User object.')
    if not isinstance(project, Project):
        raise TypeError(f'Project {project} is not a Project object.')
    if not isinstance(value, Decimal):
        raise TypeError(f'Value {value} is not a Decimal.')
    try:
        allocation_objects = get_accounting_allocation_objects(project)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(e)
        return False
    user_project_allocation = allocation_objects.allocation_user_attribute
    user_project_allocation.value = value
    user_project_allocation.save()
    return True


def set_user_project_usage_value(user, project, value):
    """Set the usage value of the usage for the compute allocation for
    the given Project; return whether or not the update was performed
    successfully.

    Parameters:
        - user (User): an instance of the User model
        - project (Project): an instance of the Project model
        - value (Decimal): the allocation value to be set

    Returns:
        - Boolean denoting success or failure

    Raises:
        - TypeError, if one or more inputs has the wrong type
    """
    if not isinstance(user, User):
        raise TypeError(f'User {user} is not a User object.')
    if not isinstance(project, Project):
        raise TypeError(f'Project {project} is not a Project object.')
    if not isinstance(value, Decimal):
        raise TypeError(f'Value {value} is not a Decimal.')
    try:
        allocation_objects = get_accounting_allocation_objects(
            project, user=user)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(e)
        return False
    user_project_usage = allocation_objects.allocation_user_attribute_usage
    user_project_usage.value = value
    user_project_usage.save()
    return True
