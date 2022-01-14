from coldfront.core.project.models import Project
from django.contrib.auth.models import User


def can_project_buy_service_units(project):
    """Return whether the given Project is eligible to buy additional
    Service Units for its allowance."""
    if not isinstance(project, Project):
        raise TypeError(f'{project} is not a Project object.')
    return project.name.startswith('ac_')


def is_user_manager_or_pi_of_project(user, project):
    """Return whether the given User is an 'Active' 'Manager' or
    'Principal Investigator' on the given Project."""
    if not isinstance(user, User):
        raise TypeError(f'{user} is not a User object.')
    if not isinstance(project, Project):
        raise TypeError(f'{project} is not a Project object.')
    return project.projectuser_set.filter(
        user=user,
        role__name__in=['Manager', 'Principal Investigator'],
        status__name='Active').exists()


def is_user_member_of_project(user, project):
    """Return whether the given User is an 'Active' member of the given
    Project."""
    if not isinstance(user, User):
        raise TypeError(f'{user} is not a User object.')
    if not isinstance(project, Project):
        raise TypeError(f'{project} is not a Project object.')
    return project.projectuser_set.filter(
        user=user, status__name='Active').exists()
