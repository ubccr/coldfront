from abc import ABC
from abc import abstractmethod
from enum import Enum
import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction

from flags.state import flag_enabled

from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AllocationUserAttribute
from coldfront.core.allocation.utils import get_or_create_active_allocation_user
from coldfront.core.allocation.utils import get_project_compute_allocation
from coldfront.core.allocation.utils_.cluster_access_utils import ClusterAccessRequestRunner
from coldfront.core.allocation.utils_.cluster_access_utils import ClusterAccessRequestRunnerValidationError
from coldfront.core.billing.models import BillingActivity
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserJoinRequest
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.utils import send_added_to_project_notification_email
from coldfront.core.project.utils import send_project_join_request_approval_email
from coldfront.core.resource.utils import get_computing_allowance_project_prefixes
from coldfront.core.user.utils_.host_user_utils import eligible_host_project_users
from coldfront.core.user.utils_.host_user_utils import lbl_email_address
from coldfront.core.user.utils_.host_user_utils import needs_host
from coldfront.core.utils.email.email_strategy import validate_email_strategy_or_get_default


logger = logging.getLogger(__name__)


def add_vector_user_to_designated_savio_project(user_obj, email_strategy=None):
    """Add the given User to the Savio project that all Vector users
    also have access to.

    This is intended for use after the user's request has been approved
    and the user has been successfully added to a Vector project.

    Only perform processing if the User is not already active on the
    Project."""
    email_strategy = validate_email_strategy_or_get_default(
        email_strategy=email_strategy)

    project_name = settings.SAVIO_PROJECT_FOR_VECTOR_USERS
    project_obj = Project.objects.get(name=project_name)

    user_role = ProjectUserRoleChoice.objects.get(name='User')
    active_status = ProjectUserStatusChoice.objects.get(name='Active')

    project_user_exists = ProjectUser.objects.filter(
        project=project_obj, user=user_obj).exists()
    with transaction.atomic():
        run_runner = False
        if project_user_exists:
            project_user_obj = project_user_exists.first()
            if project_user_obj.status != active_status:
                project_user_obj.status = active_status
                project_user_obj.save()
                run_runner = True
        else:
            project_user_obj = ProjectUser.objects.create(
                project=project_obj, user=user_obj, role=user_role,
                status=active_status, enable_notifications=False)
            run_runner = True
        if run_runner:
            runner_factory = NewProjectUserRunnerFactory()
            new_project_user_runner = runner_factory.get_runner(
                project_user_obj, NewProjectUserSource.AUTO_ADDED,
                email_strategy=email_strategy)
            new_project_user_runner.run()


class NewProjectUserSource(Enum):
    """The ways in which a ProjectUser could be newly-associated with a
    Project."""

    # The User was added by a project PI or manager.
    ADDED = 1
    # The User requested to join, and the request was approved.
    JOINED = 2
    # The User made a request to create (or pool with) the project.
    NEW_PROJECT_REQUESTER = 3
    # The User was listed as a PI on a request to create (or pool with) the
    # project, and did not make the request themselves.
    NEW_PROJECT_NON_REQUESTER_PI = 4
    # The User made a request to renew a PI's allocation under the project.
    ALLOCATION_RENEWAL_REQUESTER = 5
    # The User was listed as the PI on a request to renew a PI's allocation
    # under the project, and did not make the request themselves.
    ALLOCATION_RENEWAL_NON_REQUESTER_PI = 6
    # The User was automatically added to the project due to business logic.
    AUTO_ADDED = 7


class NewProjectUserRunner(ABC):
    """An abstract class that performs processing when a User is
    associated with a Project.

    This should only be used when a ProjectUser is created, or when it
    goes from a non-'Active' status to the 'Active' one.
    """

    @abstractmethod
    def __init__(self, project_user_obj, source, email_strategy=None):
        """Validate inputs."""
        assert isinstance(project_user_obj, ProjectUser)
        assert (
            project_user_obj.status ==
            ProjectUserStatusChoice.objects.get(name='Active'))
        assert isinstance(source, NewProjectUserSource)
        self._project_user_obj = project_user_obj

        self._source = source
        self._should_request_cluster_access = True
        self._should_allow_preexisting_cluster_access = False
        self._update_processing_options_from_source()

        self._project_obj = self._project_user_obj.project
        self._allocation_obj = get_project_compute_allocation(
            self._project_obj)
        self._user_obj = self._project_user_obj.user
        self._allocation_user_obj = None

        self._email_strategy = validate_email_strategy_or_get_default(
            email_strategy=email_strategy)

        self._success_messages = []
        self._warning_messages = []

    def get_warning_messages(self):
        """Return warning messages raised during the run."""
        return self._warning_messages.copy()

    def run(self):
        """Request cluster access, run extra processing steps as needed,
        and send notification emails."""
        with transaction.atomic():
            self._create_or_update_active_compute_allocation_user()
            if self._should_request_cluster_access:
                self._request_cluster_access()
            self._run_extra_steps()
        self._send_emails_safe()

    def _create_or_update_active_compute_allocation_user(self):
        """Create an AllocationUser under the project's 'CLUSTER_NAME
        Compute' Allocation if one does not exist. Set its status to
        'Active'."""
        self._allocation_user_obj = get_or_create_active_allocation_user(
            self._allocation_obj, self._user_obj)
        message = (
            f'Created or updated AllocationUser '
            f'{self._allocation_user_obj.pk} and set it to active.')
        self._success_messages.append(message)

    def _request_cluster_access(self):
        """Request that the User be granted access to the cluster under
        the Project."""
        project_cluster_access_request_runner = ClusterAccessRequestRunner(
            self._allocation_user_obj, email_strategy=self._email_strategy)
        try:
            project_cluster_access_request_runner.run()
        except ClusterAccessRequestRunnerValidationError as e:
            if self._should_allow_preexisting_cluster_access:
                pass
            else:
                raise e

    def _run_extra_steps(self):
        """Run extra processing steps."""
        pass

    def _send_emails(self):
        """Send the appropriate email to the new user if needed."""
        if self._source == NewProjectUserSource.ADDED:
            email_method = send_added_to_project_notification_email
        elif self._source == NewProjectUserSource.JOINED:
            email_method = send_project_join_request_approval_email
        elif self._source == NewProjectUserSource.AUTO_ADDED:
            email_method = send_added_to_project_notification_email
        else:
            return
        email_args = (self._project_obj, self._project_user_obj)
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
                f'emails. Details:\n{e}')
            logger.exception(message)

    def _update_processing_options_from_source(self):
        """Given the manner in which the User was associated with the
        Project (NewProjectUserSource), update boolean options that
        control processing logic."""
        source = self._source
        source_enum = NewProjectUserSource
        if source == source_enum.NEW_PROJECT_REQUESTER:
            self._should_allow_preexisting_cluster_access = True
        elif source == source_enum.NEW_PROJECT_NON_REQUESTER_PI:
            self._should_request_cluster_access = False
            self._should_allow_preexisting_cluster_access = True
        elif source == source_enum.ALLOCATION_RENEWAL_REQUESTER:
            self._should_allow_preexisting_cluster_access = True
        elif source == source_enum.ALLOCATION_RENEWAL_NON_REQUESTER_PI:
            self._should_request_cluster_access = False
            self._should_allow_preexisting_cluster_access = True
        elif source == source_enum.AUTO_ADDED:
            self._should_allow_preexisting_cluster_access = True


class BRCNewProjectUserRunner(NewProjectUserRunner):
    """A concrete class that performs processing when a User is
    newly-associated with a Project, including additional BRC-specific
    handling."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _run_extra_steps(self):
        """Run extra processing steps.
            1. For Vector projects, add the user to a designated project
               on the primary cluster. Allow this step to fail without
               rolling back the transaction.
        """
        if self._is_vector_project():
            try:
                add_vector_user_to_designated_savio_project(
                    self._user_obj, email_strategy=self._email_strategy)
            except Exception as e:
                message = (
                    f'Failed to automatically add User '
                    f'{self._user_obj.username} to the designated Savio '
                    f'project for Vector users.')
                self._warning_messages.append(message)
                logger.exception(message + f' Details:\n{e}')

    def _is_vector_project(self):
        """Return whether the Project is associated with the Vector
        cluster."""
        return self._project_obj.name.startswith('vector_')


class LRCNewProjectUserRunner(NewProjectUserRunner):
    """A concrete class that performs processing when a User is
    newly-associated with a Project, including additional LRC-specific
    handling."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _get_allocation_billing_attribute(self):
        """Return the AllocationAttribute with type 'Billing Activity'
        associated with the Allocation, which is expected to exist."""
        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Billing Activity')
        return self._allocation_obj.allocationattribute_set.get(
            allocation_attribute_type=allocation_attribute_type)

    def _get_allocation_user_billing_attribute(self):
        """Return the AllocationUserAttribute with type 'Billing
        Activity' associated with the AllocationUser if it exists, else
        None."""
        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Billing Activity')
        try:
            return self._allocation_user_obj.allocationuserattribute_set.get(
                allocation_attribute_type=allocation_attribute_type)
        except AllocationUserAttribute.DoesNotExist:
            return None

    def _run_extra_steps(self):
        """Run extra processing steps.
            1. For external users who require a host user, set it.
            2. For projects requiring one, set a BillingActivity.
        """
        if needs_host(self._user_obj):
            self._set_host_user()
        if self._should_set_billing_activities():
            self._set_billing_activities()

    def _set_billing_activities(self):
        """Propagate the BillingActivity of the Allocation to:
            1. The User's UserProfile, if it does not have one, and
            2. The AllocationUser's AllocationUserAttribute of type
               'Billing Activity', if one does not exist or is empty."""
        allocation_billing_attribute = self._get_allocation_billing_attribute()
        billing_activity = BillingActivity.objects.get(
            pk=int(allocation_billing_attribute.value))

        user_profile = self._user_obj.userprofile
        if not user_profile.billing_activity:
            user_profile.billing_activity = billing_activity
            user_profile.save()

        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Billing Activity')
        allocation_user_billing_attribute = \
            self._get_allocation_user_billing_attribute()
        if not isinstance(
                allocation_user_billing_attribute, AllocationUserAttribute):
            AllocationUserAttribute.objects.create(
                allocation_attribute_type=allocation_attribute_type,
                allocation=self._allocation_obj,
                allocation_user=self._allocation_user_obj,
                value=allocation_billing_attribute.value)
        elif not allocation_user_billing_attribute.value.strip():
            allocation_user_billing_attribute.value = \
                allocation_billing_attribute.value
            allocation_user_billing_attribute.save()

    def _set_host_user(self):
        """Determine and set a host_user in the ProjectUser's
        UserProfile if possible. If not, raise an exception."""
        host_user = None

        lbl_address = lbl_email_address(self._user_obj)
        if lbl_address is not None:
            # LBL employee: set host to self.
            host_user = self._user_obj
        else:
            # Non-LBL employee: set host to an LBL employee project PI.
            if self._source == NewProjectUserSource.JOINED:
                join_requests = ProjectUserJoinRequest.objects.filter(
                    project_user=self._project_user_obj,
                    host_user__isnull=False)
                if join_requests.exists():
                    host_user = join_requests.latest('modified').host_user
            if not host_user:
                eligible_hosts = eligible_host_project_users(self._project_obj)
                if eligible_hosts:
                    host_user = eligible_hosts[0].user

        if not host_user:
            message = (
                f'Failed to determine a host user to set for ProjectUser '
                f'{self._project_user_obj.pk}.')
            logger.error(message)
            raise Exception(message)

        self._user_obj.userprofile.host_user = host_user
        self._user_obj.userprofile.save()

    def _should_set_billing_activities(self):
        """Return whether billing activities need to be set."""
        computing_allowance_project_prefixes = \
            get_computing_allowance_project_prefixes()
        return self._project_obj.name.startswith(
            computing_allowance_project_prefixes)


class NewProjectUserRunnerFactory(object):
    """A factory for returning a class that performs additional
    processing when a user is added to or joins a Project. """

    def get_runner(self, *args, **kwargs):
        """Return an instantiated runner for the given ProjectUser with
        the given arguments and keyword arguments."""
        return self._get_runner_class()(*args, **kwargs)

    @staticmethod
    def _get_runner_class():
        """Return the appropriate runner class for the given
        ProjectUser. If none are applicable, raise an
        ImproperlyConfigured exception."""
        if flag_enabled('BRC_ONLY'):
            return BRCNewProjectUserRunner
        elif flag_enabled('LRC_ONLY'):
            return LRCNewProjectUserRunner
        else:
            raise ImproperlyConfigured(
                'One of the following flags must be enabled: BRC_ONLY, '
                'LRC_ONLY.')
