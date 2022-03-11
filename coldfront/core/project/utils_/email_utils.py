from coldfront.core.project.models import Project

from django.db.models import Q

"""Utilities relating to sending Project-related emails."""


def project_email_receiver_list(project):
    """For the given Project, return a list of unique email addresses,
    belonging to its active Managers, and its active PIs who have
    notifications enabled.

    Parameters:
        - project: a Project object.

    Returns:
        - A list of email addresses.

    Raises:
        - TypeError, if the given Project is not a Project object.
        - Exception, if any other errors occur.
    """
    if not isinstance(project, Project):
        raise TypeError(f'{project} is not a Project object.')
    return project.managers_and_pis_emails()
