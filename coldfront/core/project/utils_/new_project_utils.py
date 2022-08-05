from coldfront.api.statistics.utils import set_project_user_allocation_value
from coldfront.core.allocation.models import AllocationAttribute
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.allocation.models import AllocationStatusChoice
from coldfront.core.allocation.utils import get_or_create_active_allocation_user
from coldfront.core.allocation.utils import get_project_compute_allocation
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectAllocationRequestStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.project.models import VectorProjectAllocationRequest
from coldfront.core.project.signals import new_project_request_denied
from coldfront.core.project.utils import ProjectClusterAccessRequestRunner
from coldfront.core.project.utils import send_added_to_project_notification_email
from coldfront.core.resource.models import Resource
from coldfront.core.resource.utils_.allowance_utils.computing_allowance import ComputingAllowance
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.statistics.models import ProjectTransaction
from coldfront.core.statistics.models import ProjectUserTransaction
from coldfront.core.user.utils import account_activation_url
from coldfront.core.utils.common import display_time_zone_current_date
from coldfront.core.utils.common import import_from_settings
from coldfront.core.utils.common import project_detail_url
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.common import validate_num_service_units
from coldfront.core.utils.mail import send_email_template

from collections import namedtuple
from decimal import Decimal

from django.conf import settings
from django.db.models import Q
from django.urls import reverse

from urllib.parse import urljoin

import logging


logger = logging.getLogger(__name__)


def add_vector_user_to_designated_savio_project(user_obj):
    """Add the given User to the Savio project that all Vector users
    also have access to.

    This is intended for use after the user's request has been approved
    and the user has been successfully added to a Vector project."""
    project_name = settings.SAVIO_PROJECT_FOR_VECTOR_USERS
    project_obj = Project.objects.get(name=project_name)

    # Create a ProjectUser if needed; set its status to 'Active'.
    user_role = ProjectUserRoleChoice.objects.get(name='User')
    active_status = ProjectUserStatusChoice.objects.get(name='Active')
    defaults = {
        'role': user_role,
        'status': active_status,
        'enable_notifications': False,
    }
    project_user_obj, created = ProjectUser.objects.get_or_create(
        project=project_obj, user=user_obj, defaults=defaults)
    if created:
        message = (
            f'Created ProjectUser {project_user_obj.pk} between Project '
            f'{project_obj.pk} and User {user_obj.pk}.')
        logger.info(message)
    else:
        project_user_obj.status = active_status
        project_user_obj.save()

    # Send a notification email to the user if the user was not already a
    # member of the project.
    if created:
        try:
            send_added_to_project_notification_email(
                project_obj, project_user_obj)
        except Exception as e:
            message = 'Failed to send notification email. Details:'
            logger.error(message)
            logger.exception(e)

    # Request cluster access for the user.
    request_runner = ProjectClusterAccessRequestRunner(project_user_obj)
    request_runner.run()


def non_denied_new_project_request_statuses():
    """Return a queryset of ProjectAllocationRequestStatusChoices that
    do not have the name 'Denied'."""
    return ProjectAllocationRequestStatusChoice.objects.filter(
        ~Q(name='Denied'))


def pis_with_new_project_requests_pks(allocation_period,
                                      computing_allowance=None,
                                      request_status_names=[]):
    """Return a list of primary keys of PIs of new project requests for
    the given AllocationPeriod that match the given filters.

    Parameters:
        - allocation_period (AllocationPeriod): The AllocationPeriod to
                                                filter with
        - computing_allowance (Resource): An optional computing
                                          allowance to filter with
        - request_status_names (list[str]): A list of names of request
                                            statuses to filter with

    Returns:
        - A list of integers representing primary keys of matching PIs.

    Raises:
        - AssertionError, if an input has an unexpected type.
    """
    assert isinstance(allocation_period, AllocationPeriod)
    f = Q(allocation_period=allocation_period)
    if computing_allowance is not None:
        assert isinstance(computing_allowance, Resource)
        f = f & Q(computing_allowance=computing_allowance)
    if request_status_names:
        f = f & Q(status__name__in=request_status_names)
    return set(
        SavioProjectAllocationRequest.objects.filter(
            f).values_list('pi__pk', flat=True))


def project_pi_pks(computing_allowance=None, project_status_names=[]):
    """Return a list of primary keys of PI Users of Projects that match
    the given filters.

    Parameters:
        - computing_allowance (Resource): An optional computing
                                          allowance to filter with
        - project_status_names (list[str]): A list of names of Project
                                            statuses to filter with

    Returns:
        - A list of integers representing primary keys of matching PIs.

    Raises:
        - AssertionError, if an input has an unexpected type.
        - ComputingAllowanceInterfaceError, if allowance-related values
          cannot be retrieved.
    """
    project_prefix = ''
    if computing_allowance is not None:
        assert isinstance(computing_allowance, Resource)
        interface = ComputingAllowanceInterface()
        project_prefix = interface.code_from_name(computing_allowance.name)
    return set(
        ProjectUser.objects.filter(
            role__name='Principal Investigator',
            project__name__startswith=project_prefix,
            project__status__name__in=project_status_names
        ).values_list('user__pk', flat=True))


class ProjectApprovalRunner(object):
    """An object that performs necessary database changes when a new
    project request is approved."""

    def __init__(self, request_obj, *args, **kwargs):
        self.request_obj = request_obj

    def run(self):
        raise NotImplementedError('This method is not implemented.')


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
        self.deny_associated_renewal_request_if_existent()

    def deny_associated_renewal_request_if_existent(self):
        """Send a signal to deny any AllocationRenewalRequest that
        references this request."""
        kwargs = {'request_id': self.request_obj.pk}
        new_project_request_denied.send(sender=None, **kwargs)

    def deny_project(self):
        """Set the Project's status to 'Denied'."""
        project = self.request_obj.project
        project.status = ProjectStatusChoice.objects.get(name='Denied')
        project.save()
        return project

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


class ProjectProcessingRunner(object):
    """An object that performs necessary database changes when a new
    project request is processed."""

    def __init__(self, request_obj):
        self.request_obj = request_obj
        # A list of messages to display to the user.
        self.user_messages = []

    def run(self):
        self.upgrade_pi_user()
        project = self.activate_project()

        allocation, new_value = self.update_allocation()
        # In the pooling case, set the Service Units of the existing users to
        # the updated value.
        if (isinstance(self.request_obj, SavioProjectAllocationRequest) and
                self.request_obj.pool):
            self.update_existing_user_allocations(new_value)

        self.create_project_users()
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

        self.complete_request()
        self.send_email()

        self.run_extra_processing()

        return project, allocation

    def activate_project(self):
        """Set the Project's status to 'Active'."""
        project = self.request_obj.project
        project.status = ProjectStatusChoice.objects.get(name='Active')
        project.save()
        return project

    def complete_request(self):
        """Set the status of the request to 'Approved - Complete' and
        set its completion_time."""
        self.request_obj.status = \
            ProjectAllocationRequestStatusChoice.objects.get(
                name='Approved - Complete')
        self.request_obj.completion_time = utc_now_offset_aware()
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

    @staticmethod
    def create_cluster_access_request_for_requester(allocation_user):
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
                logger.warning(message)
            else:
                allocation_user_attribute.value = pending_add
                allocation_user_attribute.save()

    def create_project_users(self):
        """Create active ProjectUsers with the appropriate roles for the
        requester and/or the PI."""
        project = self.request_obj.project
        requester = self.request_obj.requester
        pi = self.request_obj.pi
        status = ProjectUserStatusChoice.objects.get(name='Active')

        if requester.pk != pi.pk:
            role = ProjectUserRoleChoice.objects.get(name='Manager')
            if project.projectuser_set.filter(user=requester).exists():
                requester_project_user = project.projectuser_set.get(
                    user=requester)
                requester_project_user.role = role
                requester_project_user.status = status
                requester_project_user.save()
            else:
                ProjectUser.objects.create(
                    project=project, user=requester, role=role, status=status)

        role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')
        if project.projectuser_set.filter(user=pi).exists():
            pi_project_user = project.projectuser_set.get(user=pi)
            pi_project_user.role = role
            pi_project_user.status = status
            pi_project_user.save()
        else:
            ProjectUser.objects.create(
                project=project, user=pi, role=role, status=status)

    def get_user_messages(self):
        """A getter for this instance's user_messages."""
        return self.user_messages

    def run_extra_processing(self):
        """Run additional subclass-specific processing."""
        pass

    def send_email(self):
        """Send a notification email to the requester and PI."""
        try:
            send_project_request_processing_email(self.request_obj)
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

    def update_existing_user_allocations(self, value):
        """Perform user-allocation-related handling. This should be
        implemented by subclasses."""
        raise NotImplementedError('This method is not implemented.')


class SavioProjectApprovalRunner(ProjectApprovalRunner):
    """An object that performs necessary database changes when a new
    Savio project request is approved."""

    def __init__(self, request_obj, num_service_units, send_email=False):
        validate_num_service_units(num_service_units)
        self.num_service_units = num_service_units
        super().__init__(request_obj)
        if self.request_obj.allocation_period:
            self.request_obj.allocation_period.assert_not_ended()
        # Note: send_email is already the name of a method.
        self.can_send_email = bool(send_email)

    def run(self):
        self.approve_request()
        if self.can_send_email:
            self.send_email()

    def approve_request(self):
        """Set the status of the request to 'Approved - Scheduled' and
        set its approval_time."""
        self.request_obj.status = \
            ProjectAllocationRequestStatusChoice.objects.get(
                name='Approved - Scheduled')
        self.request_obj.approval_time = utc_now_offset_aware()
        self.request_obj.save()

    def send_email(self):
        """Send a notification email to the requester and PI."""
        request = self.request_obj
        try:
            send_project_request_approval_email(
                request, self.num_service_units)
        except Exception as e:
            logger.error('Failed to send notification email. Details:\n')
            logger.exception(e)


class SavioProjectProcessingRunner(ProjectProcessingRunner):
    """An object that performs necessary database changes when a new
    Savio project request is processed."""

    def __init__(self, request_obj, num_service_units):
        validate_num_service_units(num_service_units)
        self.num_service_units = num_service_units
        super().__init__(request_obj)
        if self.request_obj.allocation_period:
            self.request_obj.allocation_period.assert_started()
            self.request_obj.allocation_period.assert_not_ended()
        self.computing_allowance_wrapper = ComputingAllowance(
            self.request_obj.computing_allowance)

    def update_allocation(self):
        """Perform allocation-related handling."""
        project = self.request_obj.project
        allocation_period = self.request_obj.allocation_period
        pool = self.request_obj.pool

        allocation = get_project_compute_allocation(project)
        allocation.status = AllocationStatusChoice.objects.get(name='Active')
        # If this is a new Project, set its Allocation's start dates. Always
        # set its end date.
        if not pool:
            allocation.start_date = display_time_zone_current_date()
        allocation.end_date = getattr(allocation_period, 'end_date', None)
        allocation.save()

        # Set or increase the allocation's service units.
        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Service Units')
        allocation_attribute, _ = \
            AllocationAttribute.objects.get_or_create(
                allocation_attribute_type=allocation_attribute_type,
                allocation=allocation)

        if self.computing_allowance_wrapper.has_infinite_service_units():
            new_value = settings.ALLOCATION_MAX
        else:
            if pool:
                existing_value = Decimal(allocation_attribute.value)
                new_value = existing_value + self.num_service_units
                validate_num_service_units(new_value)
            else:
                new_value = self.num_service_units
        allocation_attribute.value = str(new_value)
        allocation_attribute.save()

        # Create a ProjectTransaction to store the change in service units.
        ProjectTransaction.objects.create(
            project=project,
            date_time=utc_now_offset_aware(),
            allocation=Decimal(new_value))

        return allocation, new_value

    def update_existing_user_allocations(self, value):
        """Perform user-allocation-related handling.

        In particular, update the Service Units for existing Users to
        the given value. The requester and/or PI will have their values
        set once their cluster account requests are approved."""
        project = self.request_obj.project
        date_time = utc_now_offset_aware()
        for project_user in project.projectuser_set.all():
            user = project_user.user
            allocation_updated = set_project_user_allocation_value(
                user, project, value)
            if allocation_updated:
                ProjectUserTransaction.objects.create(
                    project_user=project_user,
                    date_time=date_time,
                    allocation=Decimal(value))


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

    # If an MOU is required, retrieve its signed status.
    computing_allowance_wrapper = ComputingAllowance(
        savio_request.computing_allowance)
    if computing_allowance_wrapper.requires_memorandum_of_understanding():
        memorandum_signed = state['memorandum_signed']
        memorandum_not_signed = memorandum_signed['status'] == 'Pending'
    else:
        memorandum_not_signed = False

    # One or more steps is pending.
    if (eligibility['status'] == 'Pending' or
            readiness['status'] == 'Pending' or
            memorandum_not_signed):
        return ProjectAllocationRequestStatusChoice.objects.get(
            name='Under Review')

    # The request has been approved, and is processing, scheduled, or complete.
    # The states 'Approved - Scheduled' and 'Approved - Complete' should only
    # be set once the request is scheduled for activation or activated.
    return ProjectAllocationRequestStatusChoice.objects.get(
        name='Approved - Processing')


def send_new_project_request_admin_notification_email(request):
    """Email admins notifying them of a new Savio or Vector
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
        detail_view_name = 'new-project-request-detail'
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


def send_new_project_request_pi_notification_email(request):
    """Send an email to the PI of the given request notifying them that
    someone has made a new ProjectAllocationRequest under their name.

    It is the caller's responsibility to ensure that the requester and
    PI are different (so the PI does not get a notification for their
    own request)."""
    email_enabled = import_from_settings('EMAIL_ENABLED', False)
    if not email_enabled:
        return

    if isinstance(request, SavioProjectAllocationRequest) and request.pool:
        subject = 'New Pooled Project Request under Your Name'
        pooling = True
    else:
        subject = 'New Project Request under Your Name'
        pooling = False
    template_name = 'email/project_request/pi_new_project_request.txt'

    requester = request.requester
    requester_str = (
        f'{requester.first_name} {requester.last_name} ({requester.email})')

    pi = request.pi
    pi_str = f'{pi.first_name} {pi.last_name}'

    if isinstance(request, SavioProjectAllocationRequest):
        detail_view_name = 'new-project-request-detail'
    elif isinstance(request, VectorProjectAllocationRequest):
        detail_view_name = 'vector-project-request-detail'
    else:
        raise TypeError(f'Request has invalid type {type(request)}.')
    center_base_url = settings.CENTER_BASE_URL
    review_url = urljoin(
        center_base_url, reverse(detail_view_name, kwargs={'pk': request.pk}))
    login_url = urljoin(center_base_url, reverse('login'))
    activation_url = account_activation_url(pi)
    password_reset_url = urljoin(center_base_url, reverse('password-reset'))

    context = {
        'PORTAL_NAME': settings.PORTAL_NAME,
        'pooling': pooling,
        'project_name': request.project.name,
        'requester_str': requester_str,
        'pi_str': pi_str,
        'review_url': review_url,
        'support_email': settings.CENTER_HELP_EMAIL,
        'pi_is_active': pi.is_active,
        'login_url': login_url,
        'activation_url': activation_url,
        'password_reset_url': password_reset_url,
    }

    sender = settings.EMAIL_SENDER
    receiver_list = [pi.email]

    send_email_template(subject, template_name, context, sender, receiver_list)


def send_project_request_approval_email(request, num_service_units):
    """Send a notification email to the requester and PI associated with
    the given project allocation request stating that the request has
    been approved, and the given number of service units will be added
    when the request is processed."""
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

    project_url = project_detail_url(request.project)
    context = {
        'allocation_period': request.allocation_period,
        'center_name': settings.CENTER_NAME,
        'num_service_units': num_service_units,
        'project_name': request.project.name,
        'project_url': project_url,
        'support_email': settings.CENTER_HELP_EMAIL,
        'signature': settings.EMAIL_SIGNATURE,
    }

    sender = settings.EMAIL_SENDER
    receiver_list = [request.requester.email, request.pi.email]
    cc = settings.REQUEST_APPROVAL_CC_LIST

    send_email_template(
        subject, template_name, context, sender, receiver_list, cc=cc)


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

    reason = request.denial_reason()

    context = {
        'center_name': settings.CENTER_NAME,
        'project_name': request.project.name,
        'reason_category': reason.category,
        'reason_justification': reason.justification,
        'support_email': settings.CENTER_HELP_EMAIL,
        'signature': settings.EMAIL_SIGNATURE,
    }

    sender = settings.EMAIL_SENDER
    receiver_list = [request.requester.email, request.pi.email]
    cc = settings.REQUEST_APPROVAL_CC_LIST

    send_email_template(
        subject, template_name, context, sender, receiver_list, cc=cc)


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
        'support_email': settings.CENTER_HELP_EMAIL,
        'signature': settings.EMAIL_SIGNATURE,
    }

    sender = settings.EMAIL_SENDER
    receiver_list = request.project.managers_and_pis_emails()
    send_email_template(subject, template_name, context, sender, receiver_list)


def send_project_request_processing_email(request):
    """Send a notification email to the requester and PI associated with
    the given project allocation request stating that the request has
    been processed."""
    email_enabled = import_from_settings('EMAIL_ENABLED', False)
    if not email_enabled:
        return

    if isinstance(request, SavioProjectAllocationRequest) and request.pool:
        subject = f'Pooled Project Request ({request.project.name}) Processed'
        template_name = (
            'email/project_request/pooled_project_request_processed.txt')
    else:
        subject = f'New Project Request ({request.project.name}) Processed'
        template_name = (
            'email/project_request/new_project_request_processed.txt')

    project_url = project_detail_url(request.project)
    context = {
        'center_name': settings.CENTER_NAME,
        'project_name': request.project.name,
        'project_url': project_url,
        'support_email': settings.CENTER_HELP_EMAIL,
        'signature': settings.EMAIL_SIGNATURE,
    }

    sender = settings.EMAIL_SENDER
    receiver_list = [request.requester.email, request.pi.email]
    cc = settings.REQUEST_APPROVAL_CC_LIST

    send_email_template(
        subject, template_name, context, sender, receiver_list, cc=cc)


class VectorProjectProcessingRunner(ProjectProcessingRunner):
    """An object that performs necessary database changes when a new
    Vector project request is processed."""

    def run_extra_processing(self):
        """Run additional subclass-specific processing."""
        # Automatically provide the requester with access to the designated
        # Savio project for Vector users.
        self.__add_user_to_savio_project()

    def update_allocation(self):
        """Perform allocation-related handling."""
        project = self.request_obj.project
        allocation = get_project_compute_allocation(project)
        allocation.status = AllocationStatusChoice.objects.get(name='Active')
        allocation.start_date = utc_now_offset_aware()
        allocation.save()
        return allocation, Decimal(settings.ALLOCATION_MIN)

    def update_existing_user_allocations(self, value):
        """Perform user-allocation-related handling."""
        pass

    def __add_user_to_savio_project(self):
        user_obj = self.request_obj.requester
        savio_project_name = settings.SAVIO_PROJECT_FOR_VECTOR_USERS
        try:
            add_vector_user_to_designated_savio_project(user_obj)
        except Exception as e:
            message = (
                f'Encountered unexpected exception when automatically '
                f'providing User {user_obj.pk} with access to Savio. Details:')
            logger.error(message)
            logger.exception(e)
            user_message = (
                f'A failure occurred when automatically adding User '
                f'{user_obj.username} to Savio project {savio_project_name} '
                f'and requesting cluster access. Please see the logs for more '
                f'information.')
        else:
            user_message = (
                f'User {user_obj.username} has automatically been added to '
                f'Savio project {savio_project_name}. A cluster access '
                f'request has automatically been made, assuming the user did '
                f'not already pending or active status.')
        self.user_messages.append(user_message)


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