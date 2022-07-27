from django.db import transaction
from flags.state import flag_enabled

from coldfront.api.statistics.utils import get_accounting_allocation_objects
from coldfront.core.allocation.models import Allocation, \
    ClusterAccessRequestStatusChoice, ClusterAccessRequest
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AllocationStatusChoice
from coldfront.core.allocation.models import AllocationUserAttribute
from coldfront.core.allocation.utils import get_or_create_active_allocation_user
from coldfront.core.allocation.utils import get_project_compute_allocation
from coldfront.core.allocation.utils import get_project_compute_resource_name
from coldfront.core.allocation.utils import review_cluster_access_requests_url
from coldfront.core.allocation.utils import set_allocation_user_attribute_value
from coldfront.core.allocation.utils_.accounting_utils import set_service_units
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.resource.utils import get_compute_resource_names
from coldfront.core.resource.utils import get_primary_compute_resource_name
from coldfront.core.utils.common import import_from_settings, \
    utc_now_offset_aware
from coldfront.core.utils.common import display_time_zone_current_date
from coldfront.core.utils.common import project_detail_url
from coldfront.core.utils.mail import send_email_template
from collections import namedtuple
from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Case, CharField, F, Value, When
from django.urls import reverse
from urllib.parse import urljoin

import logging


def annotate_queryset_with_cluster_name(queryset):
    """Given a queryset of Projects, annotate each instance with a
    character field named 'cluster_name', which denotes its parent
    cluster."""
    cluster_names = [name.lower() for name in get_compute_resource_names()]
    whens = [When(name__in=cluster_names, then=F('name'))]
    if flag_enabled('BRC_ONLY'):
        whens.append(
            When(name__startswith='vector_', then=Value('Vector')))
    return queryset.annotate(
        cluster_name=Case(
            *whens,
            default=Value(settings.PRIMARY_CLUSTER_NAME),
            output=CharField()))


def project_join_list_url():
    domain = import_from_settings('CENTER_BASE_URL')
    view = reverse('project-join-list')
    return urljoin(domain, view)


def review_project_join_requests_url(project):
    domain = import_from_settings('CENTER_BASE_URL')
    view = reverse('project-review-join-requests', kwargs={'pk': project.pk})
    return urljoin(domain, view)


def send_added_to_project_notification_email(project, project_user):
    """Send a notification email to a user stating that they have been
    added to a project by its managers."""
    email_enabled = import_from_settings('EMAIL_ENABLED', False)
    if not email_enabled:
        return

    subject = f'Added to Project {project.name}'
    template_name = 'email/added_to_project.txt'

    user = project_user.user

    context = {
        'user': user,
        'project_name': project.name,
        'support_email': settings.CENTER_HELP_EMAIL,
        'signature': settings.EMAIL_SIGNATURE,
    }
    if flag_enabled('BRC_ONLY'):
        context['include_docs_txt'] = (
            'deployments/brc/cluster_access_processing_docs.txt')
    elif flag_enabled('LRC_ONLY'):
        context['include_docs_txt'] = (
            'deployments/lrc/cluster_access_processing_docs.txt')

    sender = settings.EMAIL_SENDER
    receiver_list = [user.email]

    send_email_template(
        subject, template_name, context, sender, receiver_list)


def send_project_join_notification_email(project, project_user):
    """Send a notification email to the users of the given Project who
    have email notifications enabled stating that the given ProjectUser
    has requested to join it."""
    email_enabled = import_from_settings('EMAIL_ENABLED', False)
    if not email_enabled:
        return

    user = project_user.user

    subject = f'New request to join Project {project.name}'
    context = {'PORTAL_NAME': settings.PORTAL_NAME,
               'project_name': project.name,
               'user_string': f'{user.first_name} {user.last_name} ({user.email})',
               'signature': import_from_settings('EMAIL_SIGNATURE', ''),
               'review_url': review_project_join_requests_url(project),
               'url': project_detail_url(project)}

    receiver_list = project.managers_and_pis_emails()

    send_email_template(subject,
                        'email/new_project_join_request.txt',
                        context,
                        settings.EMAIL_SENDER,
                        receiver_list,
                        html_template='email/new_project_join_request.html')


def send_project_join_request_approval_email(project, project_user):
    """Send a notification email to a user stating that their request to
    join the given project has been approved."""
    email_enabled = import_from_settings('EMAIL_ENABLED', False)
    if not email_enabled:
        return

    subject = f'Request to Join {project.name} Approved'
    template_name = 'email/project_join_request_approved.txt'

    user = project_user.user

    context = {
        'user': user,
        'project_name': project.name,
        'support_email': settings.CENTER_HELP_EMAIL,
        'signature': settings.EMAIL_SIGNATURE,
    }
    if flag_enabled('BRC_ONLY'):
        context['include_docs_txt'] = (
            'deployments/brc/cluster_access_processing_docs.txt')
    elif flag_enabled('LRC_ONLY'):
        context['include_docs_txt'] = (
            'deployments/lrc/cluster_access_processing_docs.txt')

    sender = settings.EMAIL_SENDER
    receiver_list = [user.email]

    send_email_template(subject, template_name, context, sender, receiver_list)


def send_project_join_request_denial_email(project, project_user):
    """Send a notification email to a user stating that their request to
    join the given project has been denied."""
    email_enabled = import_from_settings('EMAIL_ENABLED', False)
    if not email_enabled:
        return

    subject = f'Request to Join {project.name} Denied'
    template_name = 'email/project_join_request_denied.txt'

    user = project_user.user

    context = {
        'user': user,
        'project_name': project.name,
        'support_email': settings.CENTER_HELP_EMAIL,
        'signature': settings.EMAIL_SIGNATURE,
    }

    sender = settings.EMAIL_SENDER
    receiver_list = [user.email]

    send_email_template(subject, template_name, context, sender, receiver_list)


def send_new_cluster_access_request_notification_email(project, project_user):
    """Send an email to admins notifying them of a new cluster access
    request from the given ProjectUser under the given Project."""
    email_enabled = import_from_settings('EMAIL_ENABLED', False)
    if not email_enabled:
        return

    subject = 'New Cluster Access Request'
    template_name = 'email/new_cluster_access_request.txt'

    user = project_user.user
    user_string = f'{user.first_name} {user.last_name} ({user.email})'

    context = {
        'project_name': project.name,
        'user_string': user_string,
        'review_url': review_cluster_access_requests_url(),
    }

    sender = settings.EMAIL_SENDER
    receiver_list = settings.EMAIL_ADMIN_LIST

    send_email_template(subject, template_name, context, sender, receiver_list)


class ProjectClusterAccessRequestRunnerError(Exception):
    """An exception class for the ProjectClusterAccessRequestRunner."""

    pass


class ProjectClusterAccessRequestRunner(object):
    """An object that performs necessary database checks and updates
    when access to a project on the cluster is requested for a given
    user."""

    logger = logging.getLogger(__name__)

    def __init__(self, project_user_obj):
        """Verify that the given ProjectUser is a ProjectUser instance.

        Parameters:
            - project_user_obj (ProjectUser): an instance of ProjectUser
        Returns: None
        Raises:
            - TypeError
        """
        if not isinstance(project_user_obj, ProjectUser):
            raise TypeError(
                f'ProjectUser {project_user_obj} has unexpected type '
                f'{type(project_user_obj)}.')
        self.project_user_obj = project_user_obj
        self.project_obj = self.project_user_obj.project
        self.user_obj = self.project_user_obj.user
        self.allocation_obj = None
        self.allocation_user_obj = None
        self.allocation_user_attribute_obj = None

    def run(self):
        """Perform checks and updates. Return whether or not all steps
        succeeded."""
        RunnerResult = namedtuple('RunnerResult', 'success error_message')
        server_error_message = (
            'Unexpected server error. Please contact an administrator.')
        success = False
        try:
            self.validate_project_user()
            self.validate_project_has_active_allocation()
            self.create_or_update_allocation_user()
            self.validate_no_existing_cluster_access()
            self.request_cluster_access()
            self.send_notification_email_to_cluster_admins()
        except (ObjectDoesNotExist, MultipleObjectsReturned) as e:
            message = (
                f'Found an unexpected number of objects (one was expected) '
                f'during processing of request for cluster access by '
                f'ProjectUser {self.project_user_obj.pk}. Details:')
            self.logger.error(message)
            self.logger.exception(e)
            error_message = server_error_message
        except ProjectClusterAccessRequestRunnerError as e:
            # Do not log here because this is done by the individual methods.
            error_message = str(e)
        except Exception as e:
            message = (
                f'Encountered unexpected exception during processing of '
                f'request for cluster access by ProjectUser '
                f'{self.project_user_obj.pk}. Details: ')
            self.logger.error(message)
            self.logger.exception(e)
            error_message = (
                'Unexpected server error. Please contact an administrator.')
        else:
            message = (
                f'Successfully processed request for cluster access by '
                f'ProjectUser {self.project_user_obj.pk}.')
            self.logger.info(message)
            success = True
            error_message = ''
        return RunnerResult(success=success, error_message=error_message)

    def validate_project_user(self):
        """Ensure that the ProjectUser has 'Active' status.

        Parameters: None
        Returns: None
        Raises:
            - ProjectUserStatusChoice.DoesNotExist
            - ProjectUserStatusChoice.MultipleObjectsReturned
            - ValueError
        """
        status = ProjectUserStatusChoice.objects.get(name='Active')
        if self.project_user_obj.status != status:
            message = f'ProjectUser {self.project_user_obj.pk} is not active.'
            self.logger.error(message)
            raise ValueError(message)
        message = f'Validated ProjectUser {self.project_user_obj.pk}.'
        self.logger.info(message)

    def validate_project_has_active_allocation(self):
        """Retrieve the compute Allocation for the Project.

        Parameters: None
        Returns: None
        Raises:
            - AllocationStatusChoice.DoesNotExist
            - Allocation.MultipleObjectsReturned
            - AllocationStatusChoice.MultipleObjectsReturned
            - ProjectClusterAccessRequestRunnerError
        """
        try:
            self.allocation_obj = get_project_compute_allocation(
                self.project_obj)
        except Allocation.DoesNotExist:
            message = f'Project {self.project_obj} has no compute Allocation.'
            self.logger.error(message)
            raise ProjectClusterAccessRequestRunnerError(message)

        status = AllocationStatusChoice.objects.get(name='Active')
        if self.allocation_obj.status != status:
            message = f'Allocation {self.allocation_obj.pk} is not active.'
            self.logger.error(message)
            raise ProjectClusterAccessRequestRunnerError(message)

        message = f'Validated Allocation {self.allocation_obj.pk}.'
        self.logger.info(message)

    def create_or_update_allocation_user(self):
        """Create an AllocationUser between the Allocation and User if
        one does not exist. Set its status to 'Active'.

        Parameters: None
        Returns: None
        Raises:
            - AllocationUserStatusChoice.DoesNotExist
            - AllocationUserStatusChoice.MultipleObjectsReturned
        """
        self.allocation_user_obj = get_or_create_active_allocation_user(
            self.allocation_obj, self.user_obj)
        message = (
            f'Created or updated AllocationUser {self.allocation_user_obj.pk} '
            f'and set it to active.')
        self.logger.info(message)

    def validate_no_existing_cluster_access(self):
        """Ensure that the User does not already have pending or active
        access to the Project on the cluster.

        Parameters: None
        Returns: None
        Raises:
            - AllocationAttributeType.DoesNotExist
            - AllocationAttributeType.MultipleObjectsReturned
            - AllocationUserAttribute.MultipleObjectsReturned
            - ProjectClusterAccessRequestRunnerError
        """
        queryset = self.allocation_user_obj.allocationuserattribute_set
        kwargs = {
            'allocation_attribute_type': AllocationAttributeType.objects.get(
                name='Cluster Account Status'),
            'value__in': ['Pending - Add', 'Processing', 'Active'],
        }
        try:
            status = queryset.get(**kwargs)
        except AllocationUserAttribute.DoesNotExist:
            message = (
                f'Validated that User {self.user_obj.pk} does not already '
                f'have a pending, processing, or active "Cluster Access '
                f'Status" attribute under Project {self.project_obj.pk}.')
            self.logger.info(message)
            return
        except AllocationUserAttribute.MultipleObjectsReturned as e:
            message = (
                f'Unexpectedly found multiple "Cluster Access Status" '
                f'attributes for User {self.user_obj.pk} under Project '
                f'{self.project_obj.pk}.')
            self.logger.error(message)
            raise e
        else:
            message = (
                f'User {self.user_obj.pk} already has a "Cluster Access '
                f'Status" attribute with value "{status.value}" under Project '
                f'{self.project_obj.pk}.')
            self.logger.error(message)
            raise ProjectClusterAccessRequestRunnerError(message)

    def request_cluster_access(self):
        """Create or update an AllocationUserAttribute with type
        "Cluster Account Status" and value "Pending - Add" for the
        AllocationUser.

        Parameters: None
        Returns: None
        Raises:
            - AllocationAttributeType.DoesNotExist
            - AllocationAttributeType.MultipleObjectsReturned
        """
        type_name = 'Cluster Account Status'
        value = 'Pending - Add'
        self.allocation_user_attribute_obj = \
            set_allocation_user_attribute_value(
                self.allocation_user_obj, type_name, value)

        pending_status = ClusterAccessRequestStatusChoice.objects.get(name='Pending - Add')

        request = ClusterAccessRequest.objects.create(
            allocation_user=self.allocation_user_obj,
            status=pending_status,
            request_time=utc_now_offset_aware(),
            host_user=self.user_obj.userprofile.host_user,
            billing_activity=self.user_obj.userprofile.billing_activity)

        # message = (
        #     f'Created or updated a "Cluster Account Status" to be pending for '
        #     f'User {self.user_obj.pk} and Project {self.project_obj.pk}.')

        message = (
            f'Created a cluster access request {request.pk} for user '
            f'{self.user_obj.username} and Project {self.project_obj.name}.')
        self.logger.info(message)

    def send_notification_email_to_cluster_admins(self):
        """Send an email to cluster administrators notifying them of the
        new request. If an error occurs, do not re-raise it.

        Parameters: None
        Returns: None
        Raises: None
        """
        try:
            send_new_cluster_access_request_notification_email(
                self.project_obj, self.project_user_obj)
        except Exception as e:
            message = f'Failed to send notification email. Details:'
            self.logger.error(message)
            self.logger.exception(e)


def deactivate_project_and_allocation(project, change_reason=None):
    """For the given Project, perform the following:
        1. Set its status to 'Inactive',
        2. Set its corresponding "CLUSTER_NAME Compute" Allocation's
           status to 'Expired', its start_date to the current date, and
           its end_date to None, and
        3. Reset the Service Units values and usages for the Allocation
           and its AllocationUsers.

    Parameters:
        - project (Project): an instance of the Project model
        - change_reason (str or None): An optional reason to set in
                                       created historical objects

    Returns:
        - None

    Raises:
        - AssertionError
        - MultipleObjectsReturned
        - ObjectDoesNotExist
        - TypeError"""
    assert isinstance(project, Project)

    if change_reason is None:
        change_reason = 'Zeroing service units during allocation expiration.'

    project.status = ProjectStatusChoice.objects.get(name='Inactive')

    accounting_allocation_objects = get_accounting_allocation_objects(
        project, enforce_allocation_active=False)
    allocation = accounting_allocation_objects.allocation
    allocation.status = AllocationStatusChoice.objects.get(name='Expired')
    allocation.start_date = display_time_zone_current_date()
    allocation.end_date = None

    num_service_units = settings.ALLOCATION_MIN
    set_su_kwargs = {
        'allocation_allowance': num_service_units,
        'allocation_usage': num_service_units,
        'allocation_change_reason': change_reason,
        'user_allowance': num_service_units,
        'user_usage': num_service_units,
        'user_change_reason': change_reason,
    }

    with transaction.atomic():
        project.save()
        allocation.save()
        set_service_units(accounting_allocation_objects, **set_su_kwargs)


def is_primary_cluster_project(project):
    """Return the Project is associated with the primary cluster."""
    project_compute_resource_name = get_project_compute_resource_name(project)
    primary_cluster_resource_name = get_primary_compute_resource_name()
    return project_compute_resource_name == primary_cluster_resource_name
