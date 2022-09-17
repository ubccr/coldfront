from decimal import Decimal
import logging

from django.conf import settings
from django.db import transaction

from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AllocationUser
from coldfront.core.allocation.models import AllocationUserAttribute
from coldfront.core.allocation.models import AllocationUserStatusChoice
from coldfront.core.allocation.models import ClusterAccessRequest
from coldfront.core.allocation.models import ClusterAccessRequestStatusChoice
from coldfront.core.allocation.utils import review_cluster_access_requests_url
from coldfront.core.allocation.utils import set_allocation_user_attribute_value
from coldfront.core.project.models import ProjectUser
from coldfront.core.resource.utils import get_primary_compute_resource
from coldfront.core.statistics.models import ProjectUserTransaction
from coldfront.core.utils.common import import_from_settings
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.email.email_strategy import SendEmailStrategy
from coldfront.core.utils.email.email_strategy import validate_email_strategy_or_get_default
from coldfront.core.utils.mail import send_email_template


logger = logging.getLogger(__name__)


class ClusterAccessRequestRunnerValidationError(Exception):
    """An exception to be raised by ClusterAccessRequestRunner when the
    underlying AllocationUser already has cluster access."""
    pass


class ClusterAccessRequestRunner(object):
    """An object that performs necessary database checks and updates
    when access to a project on the cluster is requested for a given
    user."""

    def __init__(self, allocation_user_obj, email_strategy=None):
        """Validate inputs."""
        assert isinstance(allocation_user_obj, AllocationUser)
        assert (
            allocation_user_obj.status ==
            AllocationUserStatusChoice.objects.get(name='Active'))
        self._allocation_user_obj = allocation_user_obj
        self._allocation_user_attribute_obj = None
        self._allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Cluster Account Status')

        self._project_obj = self._allocation_user_obj.allocation.project
        self._user_obj = self._allocation_user_obj.user

        self._email_strategy = validate_email_strategy_or_get_default(
            email_strategy=email_strategy)

        self._success_messages = []
        self._warning_messages = []

    def run(self):
        """Perform checks and updates."""
        with transaction.atomic():
            self._validate_no_existing_cluster_access()
            self._request_cluster_access()
        self._log_success_messages()
        self._send_emails_safe()

    def _create_cluster_access_request(self):
        """Create a ClusterAccessRequest with status 'Pending - Add'."""
        request = ClusterAccessRequest.objects.create(
            allocation_user=self._allocation_user_obj,
            status=ClusterAccessRequestStatusChoice.objects.get(
                name='Pending - Add'),
            request_time=utc_now_offset_aware())
        message = (
            f'Created a ClusterAccessRequest {request.pk} for user '
            f'{self._user_obj.pk} and Project {self._project_obj.pk}.')
        self._success_messages.append(message)

    def _create_pending_allocation_user_attribute(self):
        """Create or update an AllocationUserAttribute for the
        AllocationUser with type 'Cluster Account Status' to have status
        'Pending - Add'."""
        type_name = self._allocation_attribute_type.name
        value = 'Pending - Add'
        self._allocation_user_attribute_obj = \
            set_allocation_user_attribute_value(
                self._allocation_user_obj, type_name, value)
        message = (
            f'Created or updated a AllocationUserAttribute of type '
            f'"{type_name}" to have value {value} for User '
            f'{self._user_obj.pk} and Project {self._project_obj.pk}.')
        self._success_messages.append(message)

    def _log_success_messages(self):
        """Write success messages to the log.

        Catch all exceptions to prevent rolling back any enclosing
        transaction.

        Warning: If the enclosing transaction fails, the already-written
        log messages are not revoked."""
        try:
            for message in self._success_messages:
                logger.info(message)
        except Exception:
            pass

    def _request_cluster_access(self):
        """Request cluster access for the User under the Project."""
        self._create_pending_allocation_user_attribute()
        self._create_cluster_access_request()

    def _send_emails(self):
        """Email cluster administrators, notifying them of the new
        request."""
        email_method = send_new_cluster_access_request_notification_email
        email_args = (self._allocation_user_obj,)
        self._email_strategy.process_email(email_method, *email_args)

    def _send_emails_safe(self):
        """Send emails.

        Catch all exceptions to prevent rolling back any enclosing
        transaction.
        """
        try:
            self._send_emails()
        except Exception as e:
            message = (
                f'Encountered unexpected exception when sending notification '
                f'emails. Details: \n{e}')
            logger.exception(message)

    def _validate_no_existing_cluster_access(self):
        """Raise an exception if the User already has pending or active
        access to the Project on the cluster."""
        has_pending_or_active_status = \
            self._allocation_user_obj.allocationuserattribute_set.filter(
                allocation_attribute_type=self._allocation_attribute_type,
                value__in=['Pending - Add', 'Processing', 'Active']).exists()
        if has_pending_or_active_status:
            message = (
                f'User {self._user_obj.username} already has pending or '
                f'active access to the cluster under Project '
                f'{self._project_obj.name}.')
            raise ClusterAccessRequestRunnerValidationError(message)


class ClusterAccessRequestCompleteRunner(object):
    """An object that performs necessary database checks and updates
    when a ClusterAccessRequest is updated."""

    def __init__(self, request):
        """Verify that the given ClusterAccessRequest is a
        ClusterAccessRequest instance.

        Parameters:
            - request (ClusterAccessRequest): a ClusterAccessRequest instance
        Returns: None
        Raises:
            - TypeError
        """
        if not isinstance(request, ClusterAccessRequest):
            raise TypeError(
                f'ClusterAccessRequest {request} has unexpected type '
                f'{type(request)}.')

        self.request = request
        self.user = request.allocation_user.user
        self.allocation_user = request.allocation_user
        self.allocation = request.allocation_user.allocation
        self.project = request.allocation_user.allocation.project
        self._email_strategy = SendEmailStrategy()
        self._success_messages = []
        self._warning_messages = []

    def get_warning_messages(self):
        """Return warning messages raised during the run."""
        return self._warning_messages.copy()

    def run(self, username, cluster_uid):
        """Performs the necessary operations to complete the request."""
        with transaction.atomic():
            self._give_cluster_access_attribute()
            self._set_username(username)
            self._set_cluster_uid(cluster_uid)
            self._conditionally_set_user_service_units()

        message = (
            f'Successfully completed cluster access request {self.request.pk} '
            f'from User {self.user.email} under Project {self.project.name} '
            f'and Allocation {self.allocation.pk}. Cluster access for '
            f'{self.user.username} has been ACTIVATED.')
        self._success_messages.append(message)

        self._log_success_messages()
        self._send_emails_safe()

    def _conditionally_set_user_service_units(self):
        """If the Allocation is to the primary cluster's compute
        Resource, set the user's service units to that of the
        Allocation."""
        primary_compute_resource = get_primary_compute_resource()
        if self.allocation.resources.filter(
                pk=primary_compute_resource.pk).exists():
            self._set_user_service_units()

    def _log_success_messages(self):
        """Write success messages to the log.

        Catch all exceptions to prevent rolling back any enclosing
        transaction.

        Warning: If the enclosing transaction fails, the already-written
        log messages are not revoked."""
        try:
            for message in self._success_messages:
                logger.info(message)
        except Exception:
            pass

    def _give_cluster_access_attribute(self):
        """Activates cluster access attribute for user."""
        cluster_account_status = \
            AllocationAttributeType.objects.get(name='Cluster Account Status')
        cluster_access_attribute, _ = \
            AllocationUserAttribute.objects.get_or_create(
                allocation_attribute_type=cluster_account_status,
                allocation=self.allocation,
                allocation_user=self.allocation_user)

        cluster_access_attribute.value = 'Active'
        cluster_access_attribute.save()

        message = (f'Activated Cluster Account Status AllocationUserAttribute '
                   f'{cluster_access_attribute.pk}.')
        self._success_messages.append(message)

    def _set_cluster_uid(self, cluster_uid):
        """Sets cluster uid for user."""
        self.user.userprofile.cluster_uid = cluster_uid
        self.user.userprofile.save()

        message = (f'Set cluster uid for user {self.user.pk}.')
        self._success_messages.append(message)

    def _set_username(self, username):
        """Sets the user's new username."""
        self.user.username = username
        self.user.save()

        message = (f'Set username for user {self.user.pk}.')
        self._success_messages.append(message)

    def _set_user_service_units(self):
        """Set the AllocationUser's 'Service Units' attribute value to
        that of the Allocation."""
        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Service Units')
        allocation_service_units = self.allocation.allocationattribute_set.get(
            allocation_attribute_type=allocation_attribute_type)
        set_allocation_user_attribute_value(
            self.allocation_user, 'Service Units',
            allocation_service_units.value)

        # Create a ProjectUserTransaction to store the change in service units.
        project_user = ProjectUser.objects.get(
            user=self.user,
            project=self.project)
        project_user_transaction = ProjectUserTransaction.objects.create(
            project_user=project_user,
            date_time=utc_now_offset_aware(),
            allocation=Decimal(allocation_service_units.value))

        message = (f'Set service units for allcoation user '
                   f'{self.allocation_user.pk}. Created ProjectUserTransaction '
                   f'{project_user_transaction.pk} to record change in SUs.')
        self._success_messages.append(message)

    def _send_complete_emails(self):
        """Sends emails to the user and managers and PIs of the project."""
        email_args = (self.user, self.project)
        self._email_strategy.process_email(send_complete_cluster_access_emails,
                                           *email_args)

    def _send_emails_safe(self):
        """Send emails.

        Catch all exceptions to prevent rolling back any
        enclosing transaction.

        If send failures occur, store a warning message.
        """
        try:
            self._send_complete_emails()
        except Exception as e:
            message = (
                f'Encountered unexpected exception when sending notification '
                f'emails. Details: \n{e}')
            logger.exception(message)


class ClusterAccessRequestDenialRunner(object):
    """An object that performs necessary database checks and updates
    when a ClusterAccessRequest is denied."""

    def __init__(self, request):
        """Verify that the given ClusterAccessRequest is a ClusterAccessRequest instance.

        Parameters:
            - request (ClusterAccessRequest): an instance of ClusterAccessRequest
        Returns: None
        Raises:
            - TypeError
        """
        if not isinstance(request, ClusterAccessRequest):
            raise TypeError(
                f'ClusterAccessRequest {request} has unexpected type '
                f'{type(request)}.')

        self.request = request
        self.user = request.allocation_user.user
        self.allocation_user = self.request.allocation_user
        self.allocation = self.request.allocation_user.allocation
        self.project = request.allocation_user.allocation.project
        self._email_strategy = SendEmailStrategy()
        self._success_messages = []
        self._warning_messages = []

    def get_warning_messages(self):
        """Return warning messages raised during the run."""
        return self._warning_messages.copy()

    def run(self):
        """Denies the request."""
        with transaction.atomic():
            self._deny_cluster_access_attribute()

        message = (
            f'Successfully DENIED cluster access request {self.request.pk} '
            f'from User {self.user.email} under Project {self.project.name} '
            f'and Allocation {self.allocation.pk}.')
        self._success_messages.append(message)

        self._log_success_messages()
        self._send_emails_safe()

    def _log_success_messages(self):
        """Write success messages to the log.

        Catch all exceptions to prevent rolling back any enclosing
        transaction.

        Warning: If the enclosing transaction fails, the already-written
        log messages are not revoked."""
        try:
            for message in self._success_messages:
                logger.info(message)
        except Exception:
            pass

    def _deny_cluster_access_attribute(self):
        """Activates cluster access attribute for user."""
        cluster_account_status = \
            AllocationAttributeType.objects.get(name='Cluster Account Status')
        cluster_access_attribute, _ = \
            AllocationUserAttribute.objects.get_or_create(
                allocation_attribute_type=cluster_account_status,
                allocation=self.allocation,
                allocation_user=self.allocation_user)

        cluster_access_attribute.value = 'Denied'
        cluster_access_attribute.save()

        message = (f'Denied Cluster Account Status AllocationUserAttribute '
                   f'{cluster_access_attribute.pk}')
        self._success_messages.append(message)

    def _send_denial_emails(self):
        email_args = (self.user, self.project, self.allocation)
        self._email_strategy.process_email(send_denial_cluster_access_emails,
                                           *email_args)

    def _send_emails_safe(self):
        """Send emails.

        Catch all exceptions to prevent rolling back any
        enclosing transaction.

        If send failures occur, store a warning message.
        """
        try:
            self._send_denial_emails()
        except Exception as e:
            message = (
                f'Encountered unexpected exception when sending notification '
                f'emails. Details: \n{e}')
            logger.exception(message)


def send_complete_cluster_access_emails(user, project):
    if settings.EMAIL_ENABLED:
        subject = 'Cluster Access Activated'
        template = 'email/cluster_access_activated.txt'

        template_context = {
            'PROGRAM_NAME_SHORT': settings.PROGRAM_NAME_SHORT,
            'user': user,
            'project_name': project.name,
            'center_user_guide': settings.CENTER_USER_GUIDE,
            'center_login_guide': settings.CENTER_LOGIN_GUIDE,
            'center_help_email': settings.CENTER_HELP_EMAIL,
            'signature': settings.EMAIL_SIGNATURE,
        }

        cc_list = project.managers_and_pis_emails()

        send_email_template(
            subject,
            template,
            template_context,
            settings.EMAIL_SENDER,
            [user.email],
            cc=cc_list)


def send_denial_cluster_access_emails(user, project, allocation):
    if settings.EMAIL_ENABLED:
        subject = 'Cluster Access Denied'
        template = 'email/cluster_access_denied.txt'
        template_context = {
            'user': user,
            'center_name': import_from_settings('CENTER_NAME'),
            'project': project.name,
            'allocation': allocation.pk,
            'opt_out_instruction_url': settings.EMAIL_OPT_OUT_INSTRUCTION_URL,
            'signature': settings.EMAIL_SIGNATURE,
        }

        cc_list = project.managers_and_pis_emails()

        send_email_template(
            subject,
            template,
            template_context,
            settings.EMAIL_SENDER,
            [user.email],
            cc=cc_list)


def send_new_cluster_access_request_notification_email(allocation_user):
    """Email admins notifying them of a new cluster access request for
    the given AllocationUser."""
    email_enabled = import_from_settings('EMAIL_ENABLED', False)
    if not email_enabled:
        return

    subject = 'New Cluster Access Request'
    template_name = 'email/new_cluster_access_request.txt'

    user = allocation_user.user
    user_string = f'{user.first_name} {user.last_name} ({user.email})'

    context = {
        'project_name': allocation_user.allocation.project.name,
        'user_string': user_string,
        'review_url': review_cluster_access_requests_url(),
    }

    sender = settings.EMAIL_SENDER
    receiver_list = settings.EMAIL_ADMIN_LIST

    send_email_template(subject, template_name, context, sender, receiver_list)
