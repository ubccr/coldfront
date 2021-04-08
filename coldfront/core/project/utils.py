from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationAttribute
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AllocationStatusChoice
from coldfront.core.allocation.utils import request_project_cluster_access
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
        role__name='Principal Investigator', active=True,
        enable_notifications=True)
    manager_condition = Q(role__name='Manager', active=True)
    receiver_list = list(
        project.projectuser_set.filter(
            pi_condition | manager_condition
        ).values_list(
            'user__email', flat=True
        ))

    send_email_template(subject, template_name, context, sender, receiver_list)


def send_new_project_request_notification_email(request):
    """Send an email to admins notifying them of a new Savio or Vector
    ProjectAllocationRequest."""
    email_enabled = import_from_settings('EMAIL_ENABLED', False)
    if not email_enabled:
        return

    if request.pool:
        subject = 'New Pooled Project Request'
    else:
        subject = 'New Project Request'
    template_name = 'email/admins_new_project_request.html'

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
        'pooling': request.pool,
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

    if request.pool:
        subject = f'Pooled Project Request ({request.project.name}) Approved'
        template_name = (
            'email/project_request/pooled_project_request_approved.html')
    else:
        subject = f'New Project Request ({request.project.name}) Approved'
        template_name = (
            'email/project_request/new_project_request_approved.html')

    project_url = __project_detail_url(request.project)
    context = {
        'center_name': settings.EMAIL_CENTER_NAME,
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

    if request.pool:
        subject = f'Pooled Project Request ({request.project.name}) Denied'
        template_name = (
            'email/project_request/pooled_project_request_denied.html')
    else:
        subject = f'New Project Request ({request.project.name}) Denied'
        template_name = 'email/project_request/new_project_request_denied.html'

    project_url = __project_detail_url(request.project)
    context = {
        'center_name': settings.EMAIL_CENTER_NAME,
        'project_name': request.project.name,
        'project_url': project_url,
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
        'center_name': settings.EMAIL_CENTER_NAME,
        'project_name': request.project.name,
        'requester_str': requester_str,
        'pi_str': pi_str,
        'support_email': settings.EMAIL_TICKET_SYSTEM_ADDRESS,
        'signature': settings.EMAIL_SIGNATURE,
    }

    sender = settings.EMAIL_SENDER

    pi_condition = Q(
        role__name='Principal Investigator', active=True,
        enable_notifications=True)
    manager_condition = Q(role__name='Manager', active=True)
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
            self.logger.error('Failed to send notification email. Details:\n')
            self.logger.exception(e)

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
        """Perform allocation-related handling. In particular,

        TODO
        """
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
        """Perform allocation-related handling. In particular,

        TODO
        """
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
            self.logger.error('Failed to send notification email. Details:\n')
            self.logger.exception(e)

    def deny_project(self):
        """Set the Project's status to 'Denied'."""
        project = self.request_obj.project
        project.status = ProjectStatusChoice.objects.get(name='Denied')
        project.save()
        return project
