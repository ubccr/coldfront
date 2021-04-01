from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.utils import request_project_cluster_access
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserJoinRequest
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.utils.common import utc_now_offset_aware
from collections import namedtuple
import logging


logger = logging.getLogger(__name__)


def add_project_status_choices(apps, schema_editor):
    ProjectStatusChoice = apps.get_model('project', 'ProjectStatusChoice')

    for choice in ['New', 'Active', 'Archived', ]:
        ProjectStatusChoice.objects.get_or_create(name=choice)


def add_project_user_role_choices(apps, schema_editor):
    ProjectUserRoleChoice = apps.get_model('project', 'ProjectUserRoleChoice')

    for choice in ['User', 'Manager', ]:
        ProjectUserRoleChoice.objects.get_or_create(name=choice)


def add_project_user_status_choices(apps, schema_editor):
    ProjectUserStatusChoice = apps.get_model('project', 'ProjectUserStatusChoice')

    for choice in ['Active', 'Pending Remove', 'Denied', 'Removed', ]:
        ProjectUserStatusChoice.objects.get_or_create(name=choice)


def get_project_compute_allocation(project_obj):
    """Return the given Project's Allocation to a Compute Resource."""
    if project_obj.name.startswith('vector_'):
        resource_name = 'Vector Compute'
    else:
        resource_name = 'Savio Compute'
    return project_obj.allocation_set.get(resources__name=resource_name)


def auto_approve_project_join_requests():
    """Approve each request to join a Project that has completed its
    delay period. Return the results of each approval attempt, where
    each result has a 'success' boolean and a string message."""
    JoinAutoApprovalResult = namedtuple(
        'JoinAutoApprovalResult', 'success message')

    pending_status = ProjectUserStatusChoice.objects.get(
        name='Pending - Add')
    active_status = ProjectUserStatusChoice.objects.get(name='Active')
    project_user_objs = ProjectUser.objects.prefetch_related(
        'project', 'project__allocation_set', 'projectuserjoinrequest_set'
    ).filter(status=pending_status)

    now = utc_now_offset_aware()
    results = []

    for project_user_obj in project_user_objs:
        project_obj = project_user_obj.project
        user_obj = project_user_obj.user

        # Retrieve the latest ProjectUserJoinRequest for the ProjectUser.
        try:
            queryset = project_user_obj.projectuserjoinrequest_set
            join_request = queryset.latest('created')
        except ProjectUserJoinRequest.DoesNotExist:
            message = (
                f'ProjectUser {project_user_obj.pk} has no corresponding '
                f'ProjectUserJoinRequest.')
            logger.error(message)
            results.append(
                JoinAutoApprovalResult(success=False, message=message))
            continue

        # If the request has completed the Project's delay period, auto-
        # approve the user and request cluster access.
        delay = project_obj.joins_auto_approval_delay
        if join_request.created + delay <= now:
            # Retrieve the compute Allocation for the Project.
            try:
                allocation_obj = get_project_compute_allocation(
                    project_obj)
            except (Allocation.DoesNotExist,
                    Allocation.MultipleObjectsReturned):
                message = (
                    f'Project {project_obj.name} has no compute '
                    f'allocation.')
                logger.error(message)
                results.append(
                    JoinAutoApprovalResult(success=False, message=message))
                continue

            # Set the ProjectUser's status to 'Active'.
            project_user_obj.status = active_status
            project_user_obj.save()

            # Request cluster access for the ProjectUser.
            try:
                request_project_cluster_access(allocation_obj, user_obj)
                message = (
                    f'Created a cluster access request for User '
                    f'{user_obj.username} under Project '
                    f'{project_obj.name}.')
                logger.info(message)
                results.append(
                    JoinAutoApprovalResult(success=True, message=message))
            except ValueError:
                message = (
                    f'User {user_obj.username} already has cluster access '
                    f'under Project {project_obj.name}.')
                logger.warning(message)
                results.append(
                    JoinAutoApprovalResult(success=False, message=message))
            except Exception as e:
                message = (
                    f'Failed to request cluster access for User '
                    f'{user_obj.username} under Project '
                    f'{project_obj.name}. Details:')
                logger.error(message)
                logger.exception(e)
                results.append(
                    JoinAutoApprovalResult(success=False, message=message))

    return results
