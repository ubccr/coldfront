import logging

from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import ClusterAccessRequest
from coldfront.core.allocation.models import ClusterAccessRequestStatusChoice
from coldfront.core.allocation.utils import get_or_create_active_allocation_user
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.utils.common import utc_now_offset_aware


logger = logging.getLogger(__name__)


def create_allocation_users(allocation, requester, pi):
    """Create active AllocationUsers on the given Allocation for the
    given User objects, representing the requester and PI of a request.
    Return the created objects (requester and then PI)."""
    requester_allocation_user = None
    if requester.pk != pi.pk:
        requester_allocation_user = get_or_create_active_allocation_user(
            allocation, requester)
    pi_allocation_user = get_or_create_active_allocation_user(allocation, pi)
    return requester_allocation_user, pi_allocation_user


def create_cluster_access_request_for_requester(allocation_user):
    """Create a 'Cluster Account Status' for the given
    AllocationUser corresponding to the requester of a request.
    Additionally, create a ClusterAccessRequest."""
    allocation_attribute_type = AllocationAttributeType.objects.get(
        name='Cluster Account Status')
    pending_add = 'Pending - Add'
    # get_or_create's 'defaults' arguments are only considered if a create
    # is required.
    defaults = {
        'value': pending_add,
    }
    allocation_user_attribute, created = \
        allocation_user.allocationuserattribute_set.get_or_create(
            allocation_attribute_type=allocation_attribute_type,
            allocation=allocation_user.allocation,
            defaults=defaults)
    create_request = False
    if not created:
        if allocation_user_attribute.value == 'Active':
            message = (
                f'AllocationUser {allocation_user.pk} for requester '
                f'{allocation_user.user.pk} unexpectedly already has active '
                f'cluster access status.')
            logger.warning(message)
        else:
            allocation_user_attribute.value = pending_add
            allocation_user_attribute.save()
            create_request = True
    else:
        create_request = True

    if create_request:
        user = allocation_user.user
        ClusterAccessRequest.objects.create(
            allocation_user=allocation_user,
            status=ClusterAccessRequestStatusChoice.objects.get(
                name='Pending - Add'),
            request_time=utc_now_offset_aware(),
            host_user=user.userprofile.host_user,
            billing_activity=user.userprofile.billing_activity)


def create_project_users(project, requester, pi):
    """Create active ProjectUsers on the given Project with the
    appropriate roles for the requester and/or the PI of a request. If
    the requester is already has the 'Principal Investigator' role, do
    not give it the 'Manager' role."""
    status = ProjectUserStatusChoice.objects.get(name='Active')
    pi_role = ProjectUserRoleChoice.objects.get(name='Principal Investigator')

    if requester.pk != pi.pk:
        role = ProjectUserRoleChoice.objects.get(name='Manager')
        if project.projectuser_set.filter(user=requester).exists():
            requester_project_user = project.projectuser_set.get(
                user=requester)
            if requester_project_user.role != pi_role:
                requester_project_user.role = role
            requester_project_user.status = status
            requester_project_user.save()
        else:
            ProjectUser.objects.create(
                project=project, user=requester, role=role, status=status)

    if project.projectuser_set.filter(user=pi).exists():
        pi_project_user = project.projectuser_set.get(user=pi)
        pi_project_user.role = pi_role
        pi_project_user.status = status
        pi_project_user.save()
    else:
        ProjectUser.objects.create(
            project=project, user=pi, role=pi_role, status=status)
