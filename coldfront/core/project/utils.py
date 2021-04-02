from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.utils import request_project_cluster_access
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserJoinRequest
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.utils.common import import_from_settings
from coldfront.core.utils.mail import send_email_template
from collections import namedtuple
from datetime import datetime
from datetime import timedelta
from django.conf import settings
from django.db.models import Q
from django.urls import reverse
from urllib.parse import urljoin
import logging
import pytz


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


def get_project_compute_resource_name(project_obj):
    """Return the name of the Compute Resource that corresponds to the
    given Project."""
    if project_obj.name == 'abc':
        resource_name = 'ABC Compute'
    elif project_obj.name.startswith('vector_'):
        resource_name = 'Vector Compute'
    else:
        resource_name = 'Savio Compute'
    return resource_name


def get_project_compute_allocation(project_obj):
    """Return the given Project's Allocation to a Compute Resource."""
    resource_name = get_project_compute_resource_name(project_obj)
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

    now = datetime.utcnow().astimezone(pytz.timezone(settings.TIME_ZONE))
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


def __project_detail_url(project):
    domain = import_from_settings('CENTER_BASE_URL')
    view = reverse('project-detail', kwargs={'pk': project.pk})
    return urljoin(domain, view)


def __review_project_join_requests_url(project):
    domain = import_from_settings('CENTER_BASE_URL')
    view = reverse('project-review-join-requests', kwargs={'pk': project.pk})
    return urljoin(domain, view)


def send_project_join_notification_email(project, project_user):
    """Send a notification email to the users of the given Project who
    have email notifications enabled that the given ProjectUser has
    requested to join it."""
    email_enabled = import_from_settings('EMAIL_ENABLED', False)
    if not email_enabled:
        return

    user = project_user.user

    subject = f'New request to join Project {project.name}'
    context = {
        'project_name': project.name,
        'user_string': f'{user.first_name} {user.last_name} ({user.email})',
        'signature': import_from_settings('EMAIL_SIGNATURE', ''),
    }

    delay = project.joins_auto_approval_delay
    if delay != timedelta():
        template_name = 'email/new_project_join_request_delay.txt'
        context['url'] = __review_project_join_requests_url(project)
        context['delay'] = str(delay)
    else:
        template_name = 'email/new_project_join_request_no_delay.txt'
        context['url'] = __project_detail_url(project)

    sender = settings.EMAIL_SENDER
    receiver_list = list(project.projectuser_set.filter(
        Q(role__name='Principal Investigator', enable_notifications=True) |
        Q(role__name='Manager')).values_list('user__email', flat=True))

    send_email_template(subject, template_name, context, sender, receiver_list)
