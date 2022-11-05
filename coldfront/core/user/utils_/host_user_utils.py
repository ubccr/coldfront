from django.contrib.auth.models import User

from coldfront.core.user.models import EmailAddress


def eligible_host_project_users(project):
    """Return a list of ProjectUser objects associated with the given
    Project that are eligible to be hosts for external users.

    In particular, return active PIs who are LBL employees."""
    active_pis = project.projectuser_set.filter(
        role__name='Principal Investigator', status__name='Active').distinct()
    return [pi for pi in active_pis if is_lbl_employee(pi.user)]


def host_user_lbl_email(user):
    """Given a User, return the LBL email address of the user's host
    user if they have one, else None."""
    host_user = user.userprofile.host_user
    if not host_user:
        return None
    return lbl_email_address(host_user)


def is_lbl_employee(user):
    """Return whether the given User is an LBL employee."""
    return bool(lbl_email_address(user))


def lbl_email_address(user):
    """Return the LBL email address (str) of the given User if they have
    one, else None."""
    assert isinstance(user, User)
    email_domain = '@lbl.gov'
    if user.email.endswith(email_domain):
        return user.email
    email_addresses = EmailAddress.objects.filter(
        user=user, is_verified=True, email__endswith=email_domain).order_by(
            'email')
    if not email_addresses.exists():
        return None
    return email_addresses.first().email


def needs_host(user):
    """Return whether the given User needs a host user."""
    assert isinstance(user, User)
    return not bool(user.userprofile.host_user)

