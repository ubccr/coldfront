from django.core.mail import send_mail
from django.template.loader import render_to_string

from coldfront.api.statistics.utils import set_project_user_allocation_value
from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationAttribute
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AllocationStatusChoice
from coldfront.core.allocation.models import AllocationUserAttribute
from coldfront.core.allocation.utils import get_or_create_active_allocation_user
from coldfront.core.allocation.utils import get_project_compute_allocation
from coldfront.core.allocation.utils import next_allocation_start_datetime
from coldfront.core.allocation.utils import review_cluster_access_requests_url
from coldfront.core.allocation.utils import set_allocation_user_attribute_value
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectAllocationRequestStatusChoice
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserJoinRequest
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.project.models import VectorProjectAllocationRequest
from coldfront.core.project.signals import new_project_request_denied
from coldfront.core.project.utils_.request_utils import savio_request_denial_reason
from coldfront.core.project.utils_.request_utils import vector_request_denial_reason
from coldfront.core.statistics.models import ProjectTransaction
from coldfront.core.statistics.models import ProjectUserTransaction
from coldfront.core.user.utils import account_activation_url
from coldfront.core.utils.common import import_from_settings
from coldfront.core.utils.common import project_detail_url
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.common import validate_num_service_units
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
import iso8601
import logging


logger = logging.getLogger(__name__)


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


def __project_detail_url(project):
    domain = import_from_settings('CENTER_BASE_URL')
    view = reverse('project-detail', kwargs={'pk': project.pk})
    return urljoin(domain, view)


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
    context = {'project_name': project.name,
               'user_string': f'{user.first_name} {user.last_name} ({user.email})',
               'signature': import_from_settings('EMAIL_SIGNATURE', ''),
               'review_url': review_project_join_requests_url(project),
               'url': __project_detail_url(project)}

    receiver_list = project.managers_and_pis_emails()

    msg_plain = \
        render_to_string('email/new_project_join_request.txt',
                         context)
    msg_html = \
        render_to_string('email/new_project_join_request.html',
                         context)

    send_mail(
        subject,
        msg_plain,
        settings.EMAIL_SENDER,
        receiver_list,
        html_message=msg_html,
    )


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


def send_new_project_request_admin_notification_email(request):
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
        detail_view_name = 'savio-project-request-detail'
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

    ica = SavioProjectAllocationRequest.ICA
    recharge = SavioProjectAllocationRequest.RECHARGE

    # For ICA projects, retrieve whether or not both allocation dates are set.
    if savio_request.allocation_type == ica:
        allocation_dates = state['allocation_dates']
        allocation_dates_not_set = allocation_dates['status'] == 'Pending'
    else:
        allocation_dates_not_set = False

    # For ICA and Recharge projects, retrieve the signed status of the
    # Memorandum of Understanding.
    if savio_request.allocation_type in (ica, recharge):
        memorandum_signed = state['memorandum_signed']
        memorandum_not_signed = memorandum_signed['status'] == 'Pending'
    else:
        memorandum_not_signed = False

    # One or more steps is pending.
    if (eligibility['status'] == 'Pending' or
            readiness['status'] == 'Pending' or
            allocation_dates_not_set or
            memorandum_not_signed):
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

        self.approve_request()
        self.send_email()

        self.run_extra_processing()

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

    def update_existing_user_allocations(self, value):
        """Perform user-allocation-related handling. This should be
        implemented by subclasses."""
        raise NotImplementedError('This method is not implemented.')


class SavioProjectApprovalRunner(ProjectApprovalRunner):
    """An object that performs necessary database changes when a new
    Savio project request is approved and processed."""

    def __init__(self, request_obj, num_service_units):
        validate_num_service_units(num_service_units)
        self.num_service_units = num_service_units
        super().__init__(request_obj)

    def update_allocation(self):
        """Perform allocation-related handling."""
        project = self.request_obj.project
        allocation_type = self.request_obj.allocation_type
        pool = self.request_obj.pool

        allocation = get_project_compute_allocation(project)
        allocation.status = AllocationStatusChoice.objects.get(name='Active')
        # If this is a new Project, set its Allocation's start and end dates.
        if not pool:
            if allocation_type == SavioProjectAllocationRequest.ICA:
                dates = self.request_obj.state['allocation_dates']['dates']
                allocation.start_date = iso8601.parse_date(dates['start'])
                allocation.end_date = iso8601.parse_date(dates['end'])
            else:
                allocation.start_date = utc_now_offset_aware()
                # Only set the end date for FCAs and PCAs.
                if (allocation_type == SavioProjectAllocationRequest.FCA or
                        allocation_type == SavioProjectAllocationRequest.PCA):
                    allocation.end_date = \
                        next_allocation_start_datetime() - timedelta(seconds=1)
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


class VectorProjectApprovalRunner(ProjectApprovalRunner):
    """An object that performs necessary database changes when a new
    Vector project request is approved and processed."""

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
