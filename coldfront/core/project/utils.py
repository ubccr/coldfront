from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationAttribute
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AllocationStatusChoice
from coldfront.core.allocation.models import AllocationUserAttribute
from coldfront.core.allocation.utils import get_or_create_active_allocation_user
from coldfront.core.allocation.utils import review_cluster_access_requests_url
from coldfront.core.allocation.utils import set_allocation_user_attribute_value
from coldfront.core.project.models import ProjectAllocationRequestStatusChoice
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserJoinRequest
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.project.models import VectorProjectAllocationRequest
from coldfront.core.utils.common import import_from_settings
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.mail import send_email_template
from collections import namedtuple
from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q

from django.urls import reverse
from urllib.parse import urljoin
import logging


logger = logging.getLogger(__name__)


def add_project_status_choices(apps, schema_editor):
    ProjectStatusChoice = apps.get_model('project', 'ProjectStatusChoice')

    for choice in ['New', 'Active', 'Archived', 'Denied', ]:
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
    each result has a 'success' boolean and a string message.

    Because users are allowed to join 'New' Projects, only requests that
    are for 'Active' projects should be considered. Handling elsewhere
    should replace all join requests for a Project when it goes from
    'New' to 'Active'."""
    JoinAutoApprovalResult = namedtuple(
        'JoinAutoApprovalResult', 'success message')

    pending_status = ProjectUserStatusChoice.objects.get(
        name='Pending - Add')
    active_status = ProjectUserStatusChoice.objects.get(name='Active')
    project_active_status = ProjectStatusChoice.objects.get(name='Active')

    project_user_objs = ProjectUser.objects.prefetch_related(
        'project', 'project__allocation_set', 'projectuserjoinrequest_set'
    ).filter(status=pending_status, project__status=project_active_status)

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
            # Set the ProjectUser's status to 'Active'.
            project_user_obj.status = active_status
            project_user_obj.save()

            error_message = (
                f'Failed to request cluster access for User '
                f'{user_obj.username} under Project {project_obj.name}. '
                f'Details:')

            # Request cluster access.
            success = False
            try:
                request_runner = ProjectClusterAccessRequestRunner(
                    project_user_obj)
                runner_result = request_runner.run()
            except Exception as e:
                message = error_message
                logger.error(message)
                logger.exception(e)

            else:
                success = runner_result.success
                if success:
                    message = (
                        f'Created a cluster access request for User '
                        f'{user_obj.username} under Project '
                        f'{project_obj.name}.')
                    logger.info(message)
                else:
                    message = error_message
                    logger.error(message)
                    logger.exception(runner_result.error_message)

            results.append(
                JoinAutoApprovalResult(success=success, message=message))

            if success:
                # Send an email to the user.
                try:
                    send_project_join_request_approval_email(
                        project_obj, project_user_obj)
                except Exception as e:
                    message = 'Failed to send notification email. Details:'
                    logger.error(message)
                    logger.exception(e)

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
    have email notifications enabled stating that the given ProjectUser
    has requested to join it."""
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

    pi_condition = Q(
        role__name='Principal Investigator', status__name='Active',
        enable_notifications=True)
    manager_condition = Q(role__name='Manager', status__name='Active')
    receiver_list = list(
        project.projectuser_set.filter(
            pi_condition | manager_condition
        ).values_list(
            'user__email', flat=True
        ))

    send_email_template(subject, template_name, context, sender, receiver_list)


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
        'support_email': settings.EMAIL_TICKET_SYSTEM_ADDRESS,
        'signature': settings.EMAIL_SIGNATURE,
    }

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
        'support_email': settings.EMAIL_TICKET_SYSTEM_ADDRESS,
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


def send_new_project_request_notification_email(request):
    """Send an email to admins notifying them of a new Savio or Vector
    ProjectAllocationRequest."""
    email_enabled = import_from_settings('EMAIL_ENABLED', False)
    if not email_enabled:
        return

    if isinstance(request, SavioProjectAllocationRequest) and request.pool:
        subject = 'New Pooled Project Request'
        pooling = True
    else:
        subject = 'New Project Request'
        pooling = False
    template_name = 'email/project_request/admins_new_project_request.txt'

    requester = request.requester
    requester_str = (
        f'{requester.first_name} {requester.last_name} ({requester.email})')

    pi = request.pi
    pi_str = f'{pi.first_name} {pi.last_name} ({pi.email})'

    if isinstance(request, SavioProjectAllocationRequest):
        detail_view_name = 'savio-project-request-detail'
    elif isinstance(request, VectorProjectAllocationRequest):
        detail_view_name = 'vector-project-request-detail'
    else:
        raise TypeError(f'Request has invalid type {type(request)}.')
    review_url = urljoin(
        settings.CENTER_BASE_URL,
        reverse(detail_view_name, kwargs={'pk': request.pk}))

    context = {
        'pooling': pooling,
        'project_name': request.project.name,
        'requester_str': requester_str,
        'pi_str': pi_str,
        'review_url': review_url,
    }

    sender = settings.EMAIL_SENDER
    receiver_list = settings.EMAIL_ADMIN_LIST

    send_email_template(subject, template_name, context, sender, receiver_list)


def send_project_request_approval_email(request):
    """Send a notification email to the requester and PI associated with
    the given project allocation request stating that the request has
    been approved and processed."""
    email_enabled = import_from_settings('EMAIL_ENABLED', False)
    if not email_enabled:
        return

    if isinstance(request, SavioProjectAllocationRequest) and request.pool:
        subject = f'Pooled Project Request ({request.project.name}) Approved'
        template_name = (
            'email/project_request/pooled_project_request_approved.txt')
    else:
        subject = f'New Project Request ({request.project.name}) Approved'
        template_name = (
            'email/project_request/new_project_request_approved.txt')

    project_url = __project_detail_url(request.project)
    context = {
        'center_name': settings.CENTER_NAME,
        'project_name': request.project.name,
        'project_url': project_url,
        'support_email': settings.EMAIL_TICKET_SYSTEM_ADDRESS,
        'signature': settings.EMAIL_SIGNATURE,
    }

    sender = settings.EMAIL_SENDER
    receiver_list = [request.requester.email, request.pi.email]

    send_email_template(subject, template_name, context, sender, receiver_list)


def send_project_request_denial_email(request):
    """Send a notification email to the requester and PI associated with
    the given project allocation request stating that the request has
    been denied."""
    email_enabled = import_from_settings('EMAIL_ENABLED', False)
    if not email_enabled:
        return

    if isinstance(request, SavioProjectAllocationRequest) and request.pool:
        subject = f'Pooled Project Request ({request.project.name}) Denied'
        template_name = (
            'email/project_request/pooled_project_request_denied.txt')
    else:
        subject = f'New Project Request ({request.project.name}) Denied'
        template_name = 'email/project_request/new_project_request_denied.txt'

    if isinstance(request, SavioProjectAllocationRequest):
        reason = savio_request_denial_reason(request)
    else:
        reason = vector_request_denial_reason(request)

    context = {
        'center_name': settings.CENTER_NAME,
        'project_name': request.project.name,
        'reason_category': reason.category,
        'reason_justification': reason.justification,
        'support_email': settings.EMAIL_TICKET_SYSTEM_ADDRESS,
        'signature': settings.EMAIL_SIGNATURE,
    }

    sender = settings.EMAIL_SENDER
    receiver_list = [request.requester.email, request.pi.email]

    send_email_template(subject, template_name, context, sender, receiver_list)


def send_project_request_pooling_email(request):
    """Send a notification email to the managers and PIs of the project
    being requested to pool with stating that someone is attempting to
    pool."""
    email_enabled = import_from_settings('EMAIL_ENABLED', False)
    if not email_enabled:
        return

    if not request.pool:
        raise AssertionError('Provided request is not pooled.')

    subject = f'New request to pool with your project {request.project.name}'
    template_name = (
        'email/project_request/managers_new_pooled_project_request.txt')

    requester = request.requester
    requester_str = (
        f'{requester.first_name} {requester.last_name} ({requester.email})')

    pi = request.pi
    pi_str = f'{pi.first_name} {pi.last_name} ({pi.email})'

    context = {
        'center_name': settings.CENTER_NAME,
        'project_name': request.project.name,
        'requester_str': requester_str,
        'pi_str': pi_str,
        'support_email': settings.EMAIL_TICKET_SYSTEM_ADDRESS,
        'signature': settings.EMAIL_SIGNATURE,
    }

    sender = settings.EMAIL_SENDER

    pi_condition = Q(
        role__name='Principal Investigator', status__name='Active',
        enable_notifications=True)
    manager_condition = Q(role__name='Manager', status__name='Active')
    receiver_list = list(
        request.project.projectuser_set.filter(
            pi_condition | manager_condition
        ).values_list(
            'user__email', flat=True
        ))

    send_email_template(subject, template_name, context, sender, receiver_list)


def savio_request_latest_update_timestamp(savio_request):
    """Return the latest timestamp stored in the given
    SavioProjectAllocationRequest's 'state' field, or the empty string.

    The expected values are ISO 8601 strings, or the empty string, so
    taking the maximum should provide the correct output."""
    if not isinstance(savio_request, SavioProjectAllocationRequest):
        raise TypeError(
            f'Provided request has unexpected type {type(savio_request)}.')
    state = savio_request.state
    eligibility = state['eligibility']
    readiness = state['readiness']
    setup = state['setup']
    other = state['other']
    return max(
        eligibility['timestamp'], readiness['timestamp'], setup['timestamp'],
        other['timestamp'])


def vector_request_latest_update_timestamp(vector_request):
    """Return the latest timestamp stored in the given
    VectorProjectAllocationRequest's 'state' field, or the empty string.

    The expected values are ISO 8601 strings, or the empty string, so
    taking the maximum should provide the correct output."""
    if not isinstance(vector_request, VectorProjectAllocationRequest):
        raise TypeError(
            f'Provided request has unexpected type {type(vector_request)}.')
    state = vector_request.state
    eligibility = state['eligibility']
    setup = state['setup']
    return max(eligibility['timestamp'], setup['timestamp'])


def savio_request_denial_reason(savio_request):
    """Return the reason why the given SavioProjectAllocationRequest was
    denied, based on its 'state' field."""
    if not isinstance(savio_request, SavioProjectAllocationRequest):
        raise TypeError(
            f'Provided request has unexpected type {type(savio_request)}.')
    if savio_request.status.name != 'Denied':
        raise ValueError(
            f'Provided request has unexpected status '
            f'{savio_request.status.name}.')

    state = savio_request.state
    eligibility = state['eligibility']
    readiness = state['readiness']
    other = state['other']

    DenialReason = namedtuple(
        'DenialReason', 'category justification timestamp')

    if other['timestamp']:
        category = 'Other'
        justification = other['justification']
        timestamp = other['timestamp']
    elif eligibility['status'] == 'Denied':
        category = 'PI Ineligible'
        justification = eligibility['justification']
        timestamp = eligibility['timestamp']
    elif readiness['status'] == 'Denied':
        category = 'Readiness Criteria Unsatisfied'
        justification = readiness['justification']
        timestamp = readiness['timestamp']
    else:
        raise ValueError('Provided request has an unexpected state.')

    return DenialReason(
        category=category, justification=justification, timestamp=timestamp)


def vector_request_denial_reason(vector_request):
    """Return the reason why the given VectorProjectAllocationRequest
    was denied, based on its 'state' field."""
    if not isinstance(vector_request, VectorProjectAllocationRequest):
        raise TypeError(
            f'Provided request has unexpected type {type(vector_request)}.')
    if vector_request.status.name != 'Denied':
        raise ValueError(
            f'Provided request has unexpected status '
            f'{vector_request.status.name}.')

    state = vector_request.state
    eligibility = state['eligibility']

    DenialReason = namedtuple(
        'DenialReason', 'category justification timestamp')

    if eligibility['status'] == 'Denied':
        category = 'Requester Ineligible'
        justification = eligibility['justification']
        timestamp = eligibility['timestamp']
    else:
        raise ValueError('Provided request has an unexpected state.')

    return DenialReason(
        category=category, justification=justification, timestamp=timestamp)


def savio_request_state_status(savio_request):
    """Return a ProjectAllocationRequestStatusChoice, based on the
    'state' field of the given SavioProjectAllocationRequest."""
    if not isinstance(savio_request, SavioProjectAllocationRequest):
        raise TypeError(
            f'Provided request has unexpected type {type(savio_request)}.')

    state = savio_request.state
    eligibility = state['eligibility']
    readiness = state['readiness']
    other = state['other']

    # The PI was ineligible, the project did not satisfy the readiness
    # criteria, or the request was denied for some non-listed reason.
    if (eligibility['status'] == 'Denied' or
            readiness['status'] == 'Denied' or
            other['timestamp']):
        return ProjectAllocationRequestStatusChoice.objects.get(name='Denied')

    # PI eligibility or readiness are not yet determined.
    if eligibility['status'] == 'Pending' or readiness['status'] == 'Pending':
        return ProjectAllocationRequestStatusChoice.objects.get(
            name='Under Review')

    # The request has been approved, and is processing or complete. The final
    # state, 'Approved - Complete', should only be set once the request is
    # finally activated.
    return ProjectAllocationRequestStatusChoice.objects.get(
        name='Approved - Processing')


def vector_request_state_status(vector_request):
    """Return a ProjectAllocationRequestStatusChoice, based on the
    'state' field of the given VectorProjectAllocationRequest."""
    if not isinstance(vector_request, VectorProjectAllocationRequest):
        raise TypeError(
            f'Provided request has unexpected type {type(vector_request)}.')

    state = vector_request.state
    eligibility = state['eligibility']

    # The requester was ineligible.
    if eligibility['status'] == 'Denied':
        return ProjectAllocationRequestStatusChoice.objects.get(name='Denied')

    # Requester eligibility is not yet determined.
    if eligibility['status'] == 'Pending':
        return ProjectAllocationRequestStatusChoice.objects.get(
            name='Under Review')

    # The request has been approved, and is processing or complete. The final
    # state, 'Approved - Complete', should only be set once the request is
    # finally activated.
    return ProjectAllocationRequestStatusChoice.objects.get(
        name='Approved - Processing')


class ProjectApprovalRunner(object):
    """An object that performs necessary database changes when a new
    project request is approved and processed."""

    def __init__(self, request_obj):
        self.request_obj = request_obj

    def run(self):
        self.upgrade_pi_user()
        project = self.activate_project()
        self.create_project_users()
        allocation = self.update_allocation()
        requester_allocation_user, pi_allocation_user = \
            self.create_allocation_users(allocation)

        # If the AllocationUser for the requester was not created, then
        # the PI was the requester.
        if requester_allocation_user is None:
            self.create_cluster_access_request_for_requester(
                pi_allocation_user)
        else:
            self.create_cluster_access_request_for_requester(
                requester_allocation_user)

        self.approve_request()
        self.send_email()
        return project, allocation

    def activate_project(self):
        """Set the Project's status to 'Active'."""
        project = self.request_obj.project
        project.status = ProjectStatusChoice.objects.get(name='Active')
        project.save()
        return project

    def approve_request(self):
        """Set the status of the request to 'Approved - Complete'."""
        self.request_obj.status = \
            ProjectAllocationRequestStatusChoice.objects.get(
                name='Approved - Complete')
        self.request_obj.save()

    def create_allocation_users(self, allocation):
        """Create active AllocationUsers for the requester and/or the
        PI. Return the created objects (requester and then PI)."""
        requester = self.request_obj.requester
        pi = self.request_obj.pi
        requester_allocation_user = None
        if requester.pk != pi.pk:
            requester_allocation_user = get_or_create_active_allocation_user(
                allocation, requester)
        pi_allocation_user = get_or_create_active_allocation_user(
            allocation, pi)
        return requester_allocation_user, pi_allocation_user

    def create_cluster_access_request_for_requester(self, allocation_user):
        """Create a 'Cluster Account Status' for the given
        AllocationUser corresponding to the request's requester."""
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
        if not created:
            if allocation_user_attribute.value == 'Active':
                message = (
                    f'AllocationUser {allocation_user.pk} for requester '
                    f'{allocation_user.user.pk} unexpectedly already has '
                    f'active cluster access status.')
                self.logger.warning(message)
            else:
                allocation_user_attribute.value = pending_add
                allocation_user_attribute.save()

    def create_project_users(self):
        """Create active ProjectUsers with the appropriate roles for the
        requester and/or the PI."""
        project = self.request_obj.project
        requester = self.request_obj.requester
        pi = self.request_obj.pi
        # get_or_create's 'defaults' arguments are only considered if a create
        # is required.
        defaults = {
            'status': ProjectUserStatusChoice.objects.get(name='Active')
        }
        if requester.pk != pi.pk:
            defaults['role'] = ProjectUserRoleChoice.objects.get(
                name='Manager')
            requester_project_user, _ = ProjectUser.objects.get_or_create(
                project=project, user=requester, defaults=defaults)
        defaults['role'] = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')
        pi_project_user, _ = ProjectUser.objects.get_or_create(
            project=project, user=pi, defaults=defaults)

    def send_email(self):
        """Send a notification email to the requester and PI."""
        try:
            send_project_request_approval_email(self.request_obj)
        except Exception as e:
            logger.error('Failed to send notification email. Details:\n')
            logger.exception(e)

    def update_allocation(self):
        """Perform allocation-related handling. This should be
        implemented by subclasses."""
        raise NotImplementedError('This method is not implemented.')

    def upgrade_pi_user(self):
        """Set the is_pi field of the request's PI UserProfile to
        True."""
        pi = self.request_obj.pi
        pi.userprofile.is_pi = True
        pi.userprofile.save()


class SavioProjectApprovalRunner(ProjectApprovalRunner):
    """An object that performs necessary database changes when a new
    Savio project request is approved and processed."""

    def __init__(self, request_obj, num_service_units):
        self.__validate_num_service_units(num_service_units)
        self.num_service_units = num_service_units
        super().__init__(request_obj)

    def update_allocation(self):
        """Perform allocation-related handling."""
        project = self.request_obj.project
        allocation_type = self.request_obj.allocation_type
        pool = self.request_obj.pool

        allocation = get_project_compute_allocation(project)
        allocation.status = AllocationStatusChoice.objects.get(name='Active')
        # TODO: Set start_date and end_date.
        # allocation.start_date = utc_now_offset_aware()
        # allocation.end_date =
        allocation.save()

        # Set the allocation's allocation type.
        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Savio Allocation Type')
        allocation_attribute, _ = \
            AllocationAttribute.objects.get_or_create(
                allocation_attribute_type=allocation_attribute_type,
                allocation=allocation, defaults={'value': allocation_type})

        # Set or increase the allocation's service units.
        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Service Units')
        allocation_attribute, _ = \
            AllocationAttribute.objects.get_or_create(
                allocation_attribute_type=allocation_attribute_type,
                allocation=allocation)
        if allocation_type == SavioProjectAllocationRequest.CO:
            # For Condo, set the value manually.
            new_value = settings.ALLOCATION_MAX
        else:
            if pool:
                existing_value = Decimal(allocation_attribute.value)
                new_value = existing_value + self.num_service_units
                self.__validate_num_service_units(new_value)
            else:
                new_value = self.num_service_units
        allocation_attribute.value = str(new_value)

        allocation_attribute.save()

        return allocation

    @staticmethod
    def __validate_num_service_units(num_service_units):
        """Raise exceptions if the given number of service units does
        not conform to the expected constraints."""
        if not isinstance(num_service_units, Decimal):
            raise TypeError(
                f'Number of service units {num_service_units} is not a '
                f'Decimal.')
        if not (settings.ALLOCATION_MIN <= num_service_units <=
                settings.ALLOCATION_MAX):
            raise ValueError(
                f'Number of service units is not in the acceptable range '
                f'[{settings.ALLOCATION_MIN}, {settings.ALLOCATION_MAX}].')
        num_service_units_tuple = num_service_units.as_tuple()
        if len(num_service_units_tuple.digits) > settings.DECIMAL_MAX_DIGITS:
            raise ValueError(
                f'Number of service units has greater than '
                f'{settings.DECIMAL_MAX_DIGITS} digits.')
        if abs(num_service_units_tuple.exponent) > settings.DECIMAL_MAX_PLACES:
            raise ValueError(
                f'Number of service units has greater than '
                f'{settings.DECIMAL_MAX_PLACES} decimal places.')


class VectorProjectApprovalRunner(ProjectApprovalRunner):
    """An object that performs necessary database changes when a new
    Vector project request is approved and processed."""

    def update_allocation(self):
        """Perform allocation-related handling."""
        project = self.request_obj.project
        allocation = get_project_compute_allocation(project)
        allocation.status = AllocationStatusChoice.objects.get(name='Active')
        # TODO: Set start_date and end_date.
        # allocation.start_date = utc_now_offset_aware()
        # allocation.end_date =
        allocation.save()
        return allocation


class ProjectDenialRunner(object):
    """An object that performs necessary database changes when a new
    project request is denied."""

    def __init__(self, request_obj):
        self.request_obj = request_obj

    def run(self):
        # Only update the Project if pooling is not involved.
        if (isinstance(self.request_obj, VectorProjectAllocationRequest) or
                not self.request_obj.pool):
            self.deny_project()
        self.deny_request()
        self.send_email()

    def deny_request(self):
        """Set the status of the request to 'Denied'."""
        self.request_obj.status = \
            ProjectAllocationRequestStatusChoice.objects.get(name='Denied')
        self.request_obj.save()

    def send_email(self):
        """Send a notification email to the requester and PI."""
        try:
            send_project_request_denial_email(self.request_obj)
        except Exception as e:
            logger.error('Failed to send notification email. Details:\n')
            logger.exception(e)

    def deny_project(self):
        """Set the Project's status to 'Denied'."""
        project = self.request_obj.project
        project.status = ProjectStatusChoice.objects.get(name='Denied')
        project.save()
        return project


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
            'value__in': ['Pending - Add', 'Active'],
        }
        try:
            status = queryset.get(**kwargs)
        except AllocationUserAttribute.DoesNotExist:
            message = (
                f'Validated that User {self.user_obj.pk} does not already '
                f'have a pending or active "Cluster Access Status" attribute '
                f'under Project {self.project_obj.pk}.')
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
        message = (
            f'Created or updated a "Cluster Account Status" to be pending for '
            f'User {self.user_obj.pk} and Project {self.project_obj.pk}.')
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
