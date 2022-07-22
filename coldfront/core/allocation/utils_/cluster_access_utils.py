from decimal import Decimal

from django.db import transaction

from coldfront.core.allocation.models import ClusterAccessRequestStatusChoice, \
    ClusterAccessRequest
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AllocationUserAttribute
from coldfront.core.allocation.utils import set_allocation_user_attribute_value
from coldfront.core.project.models import ProjectUser
from coldfront.core.statistics.models import ProjectUserTransaction
from coldfront.core.utils.common import import_from_settings, \
    utc_now_offset_aware
from coldfront.core.utils.mail import send_email_template
from django.conf import settings

import logging

logger = logging.getLogger(__name__)


class ProjectClusterAccessRequestCompleteRunner(object):
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
        self._success_messages = []
        self._warning_messages = []

    def get_warning_messages(self):
        """Return warning messages raised during the run."""
        return self._warning_messages.copy()

    def run(self, username, cluster_uid, completion_time):
        """Performs the necessary operations to complete the request."""
        with transaction.atomic():
            self._give_cluster_access_attribute()
            self._set_username(username)
            self._set_cluster_uid(cluster_uid)
            self._set_completion_time(completion_time)

            # For Savio projects, set the user's service units to that of
            # the allocation. Attempt this before setting the status to
            # 'Active' so that failures block completion.
            if not self.project.name.startswith(('abc', 'vector_')):
                self._set_user_service_units()
            self._update_request('Active')

        message = (
            f'Successfully completed cluster access request {self.request.pk} '
            f'from User {self.user.email} under Project {self.project.name} '
            f'and Allocation {self.allocation.pk}. Cluster access for '
            f'{self.user.username} has been ACTIVATED.')
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

    def _update_request(self, status_name):
        """Updates the ClusterAccessRequest with the given status name."""
        status = ClusterAccessRequestStatusChoice.objects.get(name=status_name)
        self.request.status = status
        self.request.save()

        message = (
            f'Updated cluster access request {self.request.pk} to '
            f'"{status_name}".')
        self._success_messages.append(message)

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

    def _set_completion_time(self, completion_time):
        """Sets the completion time of request."""
        self.request.completion_time = completion_time
        self.request.save()

        message = (f'Set completion time of request {self.request.pk}.')
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
        success = False
        if settings.EMAIL_ENABLED:
            subject = 'Cluster Access Activated'
            template = 'email/cluster_access_activated.txt'

            template_context = {
                'PROGRAM_NAME_SHORT': settings.PROGRAM_NAME_SHORT,
                'user': self.user,
                'project_name': self.project.name,
                'center_user_guide': settings.CENTER_USER_GUIDE,
                'center_login_guide': settings.CENTER_LOGIN_GUIDE,
                'center_help_email': settings.CENTER_HELP_EMAIL,
                'signature': settings.EMAIL_SIGNATURE,
            }

            cc_list = self.project.managers_and_pis_emails()

            try:
                send_email_template(
                    subject,
                    template,
                    template_context,
                    settings.EMAIL_SENDER,
                    [self.user.email],
                    cc=cc_list)
                success = True
            except Exception as e:
                message = (
                    f'Failed to send a notification email to {self.user.email}.'
                    f' Details: \n{e}')
                logger.exception(message)
                success = False

        return success

    def _send_emails_safe(self):
        """Send emails.

        Catch all exceptions to prevent rolling back any
        enclosing transaction.

        If send failures occur, store a warning message.
        """
        try:
            success = self._send_complete_emails()
        except Exception as e:
            message = (
                f'Encountered unexpected exception when sending notification '
                f'emails. Details: \n{e}')
            logger.exception(message)
        else:
            if not success:
                message = f'Failed to send notification emails.'
                self._warning_messages.append(message)


class ProjectClusterAccessRequestDenialRunner(object):
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
        self._success_messages = []
        self._warning_messages = []

    def get_warning_messages(self):
        """Return warning messages raised during the run."""
        return self._warning_messages.copy()

    def run(self):
        """Denies the request."""
        with transaction.atomic():
            self._deny_cluster_access_attribute()
            self._set_status()
            self._set_completion_time(utc_now_offset_aware())

        self._log_success_messages()
        self._send_emails_safe()

        message = (
            f'Successfully DENIED cluster access request {self.request.pk} '
            f'from User {self.user.email} under Project {self.project.name} '
            f'and Allocation {self.allocation.pk}.')
        logger.info(message)

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

    def _set_status(self):
        """Updates the ClusterAccessRequest with the status name Denied."""
        status = ClusterAccessRequestStatusChoice.objects.get(name='Denied')
        self.request.status = status
        self.request.save()

        message = (f'Set status of request {self.request.pk} to Denied.')
        self._success_messages.append(message)

    def _set_completion_time(self, completion_time):
        """Sets the completion time of request."""
        self.request.completion_time = completion_time
        self.request.save()

        message = (f'Set completion time of request {self.request.pk}.')
        self._success_messages.append(message)

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
        success = False
        if settings.EMAIL_ENABLED:
            subject = 'Cluster Access Denied'
            template = 'email/cluster_access_denied.txt'
            template_context = {
                'user': self.user,
                'center_name': import_from_settings('CENTER_NAME'),
                'project': self.project.name,
                'allocation': self.allocation.pk,
                'opt_out_instruction_url': settings.EMAIL_OPT_OUT_INSTRUCTION_URL,
                'signature': settings.EMAIL_SIGNATURE,
            }

            cc_list = self.project.managers_and_pis_emails()

            try:
                send_email_template(
                    subject,
                    template,
                    template_context,
                    settings.EMAIL_SENDER,
                    [self.user.email],
                    cc=cc_list)
                success = True
            except Exception as e:
                message = (
                    f'Failed to send a notification email to {self.user.email}.'
                    f' Details: \n{e}')
                logger.exception(message)
                success = False

        return success

    def _send_emails_safe(self):
        """Send emails.

        Catch all exceptions to prevent rolling back any
        enclosing transaction.

        If send failures occur, store a warning message.
        """
        try:
            success = self._send_denial_emails()
        except Exception as e:
            message = (
                f'Encountered unexpected exception when sending notification '
                f'emails. Details: \n{e}')
            logger.exception(message)
        else:
            if not success:
                message = f'Failed to send notification emails.'
                self._warning_messages.append(message)
