from coldfront.api.statistics.utils import get_accounting_allocation_objects
from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from decimal import Decimal
from django.conf import settings
from django.contrib.auth.models import User


def get_current_allocation_period():
    # TODO: Account for other periods.
    return AllocationPeriod.objects.get(name='AY21-22')


def get_pi_current_active_fca_project(pi_user):
    # TODO: This is flawed because PI "A" could be on a Project where a
    # TODO: different PI "B" has renewed, but "A" hasn't. The "Service Units"
    # TODO: would be non-zero.
    # TODO: Use AllocationRenewalRequest objects instead.
    """Given a User object representing a PI, return its current,
    active fc_ Project.

    A Project is considered "active" if it has a non-zero allocation
    of "Service Units". If there are zero or multiple such Projects,
    raise an exception.

    Parameters:
        - pi_user: a User object.

    Returns:
        - A Project object.

    Raises:
        - Project.DoesNotExist, if none are found.
        - Project.MultipleObjectsReturned, if multiple are found.
        - Exception, if any other errors occur.
    """
    role = ProjectUserRoleChoice.objects.get(name='Principal Investigator')
    status = ProjectUserStatusChoice.objects.get(name='Active')
    project_users = ProjectUser.objects.select_related('project').filter(
        project__name__startswith='fc_', role=role, status=status,
        user=pi_user)
    active_fca_projects = []
    for project_user in project_users:
        project = project_user.project
        allocation_objects = get_accounting_allocation_objects(project)
        num_service_units = Decimal(
            allocation_objects.allocation_attribute.value)
        if num_service_units > settings.ALLOCATION_MIN:
            active_fca_projects.append(project)
    n = len(active_fca_projects)
    if n == 0:
        raise Project.DoesNotExist('No active FCA Project found.')
    elif n == 2:
        raise Project.MultipleObjectsReturned(
            'More than one active FCA Project found.')
    return active_fca_projects[0]


def has_non_denied_renewal_request(pi, allocation_period):
    """Return whether or not the given PI User has a non-"Denied"
    AllocationRenewalRequest for the given AllocationPeriod."""
    if not isinstance(pi, User):
        raise TypeError(f'{pi} is not a User object.')
    if not isinstance(allocation_period, AllocationPeriod):
        raise TypeError(
            f'{allocation_period} is not an AllocationPeriod object.')
    return AllocationRenewalRequest.objects.filter(
        pi=pi,
        allocation_period=allocation_period,
        status__name__in=['Under Review', 'Approved', 'Complete']).exists()


def is_pooled(project):
    """Return whether the given Project is a pooled project. In
    particular, an Project is pooled if it has more than one PI."""
    pi_role = ProjectUserRoleChoice.objects.get(
        name='Principal Investigator')
    return project.projectuser_set.filter(role=pi_role).count() > 1


def is_any_project_pi_renewable(project, allocation_period):
    """Return whether the Project has at least one PI who is eligible to
    make an AllocationRenewalRequest during the given
    AllocationPeriod."""
    for pi in project.pis():
        if not has_non_denied_renewal_request(pi, allocation_period):
            return True
    return False


class AllocationRenewalApprovalRunner(object):
    """An object that performs necessary database changes when an
    AllocationRenewalRequest is approved and processed."""

    def __init__(self, request_obj, num_service_units):
        # TODO
        pass
