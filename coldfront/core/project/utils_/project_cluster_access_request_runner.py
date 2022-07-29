import logging

from django.db import transaction

from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import ClusterAccessRequest
from coldfront.core.allocation.models import ClusterAccessRequestStatusChoice
from coldfront.core.allocation.utils import get_or_create_active_allocation_user
from coldfront.core.allocation.utils import get_project_compute_allocation
from coldfront.core.allocation.utils import set_allocation_user_attribute_value
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.utils import send_new_cluster_access_request_notification_email
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.email.email_strategy import EmailStrategy
from coldfront.core.utils.email.email_strategy import SendEmailStrategy


logger = logging.getLogger(__name__)


class ProjectClusterAccessRequestRunner(object):
    """An object that performs necessary database checks and updates
    when access to a project on the cluster is requested for a given
    user."""

    def __init__(self, project_user_obj, email_strategy=None):
        """Validate inputs."""
        assert isinstance(project_user_obj, ProjectUser)
        assert (
            project_user_obj.status ==
            ProjectUserStatusChoice.objects.get(name='Active'))
        self.project_user_obj = project_user_obj
        self.project_obj = self.project_user_obj.project
        self.user_obj = self.project_user_obj.user
        self.allocation_obj = get_project_compute_allocation(self.project_obj)
        self.allocation_user_obj = None
        self.allocation_user_attribute_obj = None
        self._allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Cluster Account Status')

        if email_strategy is not None:
            assert isinstance(email_strategy, EmailStrategy)
            self._email_strategy = email_strategy
        else:
            self._email_strategy = SendEmailStrategy()

        self._success_messages = []
        self._warning_messages = []

    def run(self):
        """Perform checks and updates."""
        with transaction.atomic():
            self._create_or_update_allocation_user()
            self._validate_no_existing_cluster_access()
            self._request_cluster_access()
        self._log_success_messages()
        self._send_emails_safe()

    def _create_cluster_access_request(self):
        """Create a ClusterAccessRequest with status 'Pending - Add'."""
        request = ClusterAccessRequest.objects.create(
            allocation_user=self.allocation_user_obj,
            status=ClusterAccessRequestStatusChoice.objects.get(
                name='Pending - Add'),
            request_time=utc_now_offset_aware(),
            host_user=self.user_obj.userprofile.host_user,
            billing_activity=self.user_obj.userprofile.billing_activity)
        message = (
            f'Created a ClusterAccessRequest {request.pk} for user '
            f'{self.user_obj.pk} and Project {self.project_obj.pk}.')
        self._success_messages.append(message)

    def _create_or_update_allocation_user(self):
        """Create an AllocationUser between the Allocation and User if
        one does not exist. Set its status to 'Active'."""
        self.allocation_user_obj = get_or_create_active_allocation_user(
            self.allocation_obj, self.user_obj)
        message = (
            f'Created or updated AllocationUser {self.allocation_user_obj.pk} '
            f'and set it to active.')
        self._success_messages.append(message)

    def _create_pending_allocation_user_attribute(self):
        """Create or update an AllocationUserAttribute for the
        AllocationUser with type 'Cluster Account Status' to have status
        'Pending - Add'."""
        type_name = self._allocation_attribute_type.name
        value = 'Pending - Add'
        self.allocation_user_attribute_obj = \
            set_allocation_user_attribute_value(
                self.allocation_user_obj, type_name, value)
        message = (
            f'Created or updated a AllocationUserAttribute of type '
            f'"{type_name}" to have value {value} for User {self.user_obj.pk} '
            f'and Project {self.project_obj.pk}.')
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
        email_args = (self.project_obj, self.project_user_obj)
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
        """Assert that the User does not already have pending or active
        access to the Project on the cluster."""
        has_pending_or_active_status = \
            self.allocation_user_obj.allocationuserattribute_set.filter(
                allocation_attribute_type=self._allocation_attribute_type,
                value__in=['Pending - Add', 'Processing', 'Active']).exists()
        message = (
            f'User {self.user_obj.username} already has pending or active '
            f'access to the cluster under Project {self.project_obj.name}.')
        assert not has_pending_or_active_status, message
