from abc import ABC
from abc import abstractmethod
from collections import deque
from enum import Enum
import logging

from django.core.exceptions import ImproperlyConfigured
from django.db import transaction

from flags.state import flag_enabled

from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserJoinRequest
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.utils import send_added_to_project_notification_email
from coldfront.core.project.utils import send_project_join_request_approval_email
from coldfront.core.project.utils_.new_project_utils import add_vector_user_to_designated_savio_project
from coldfront.core.project.utils_.project_cluster_access_request_runner import ProjectClusterAccessRequestRunner
from coldfront.core.resource.utils_.allowance_utils.computing_allowance import ComputingAllowance
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.user.utils import eligible_host_project_users
from coldfront.core.user.utils import needs_host
from coldfront.core.utils.email.email_strategy import EmailStrategy
from coldfront.core.utils.email.email_strategy import SendEmailStrategy


logger = logging.getLogger(__name__)


class NewProjectUserSource(Enum):
    """The ways in which a ProjectUser could be newly-associated with a
    Project."""

    # The User was added by a project PI or manager.
    ADDED = 1
    # The User requested to join, and the request was approved.
    JOINED = 2


class NewProjectUserRunner(ABC):
    """An abstract class that performs processing when a User is
    newly-associated with a Project."""

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
        self._project_obj = self._project_user_obj.project
        self._user_obj = self._project_user_obj.user

        if email_strategy is not None:
            assert isinstance(email_strategy, EmailStrategy)
            self._email_strategy = email_strategy
        else:
            self._email_strategy = SendEmailStrategy()

    def run(self):
        """Request cluster access, run extra processing steps as needed,
        and send notification emails."""
        with transaction.atomic():
            self._request_cluster_access()
            self._run_extra_steps()
        self._send_emails_safe()

    def _request_cluster_access(self):
        """Request that the User be granted access to the cluster under
        the Project."""
        project_cluster_access_request_runner = \
            ProjectClusterAccessRequestRunner(
                self._project_user_obj, email_strategy=self._email_strategy)
        project_cluster_access_request_runner.run()

    def _run_extra_steps(self):
        """Run extra processing steps."""
        pass

    def _send_emails(self):
        """Send the appropriate email to the new user."""
        if self._source == NewProjectUserSource.ADDED:
            email_method = send_added_to_project_notification_email
        else:
            email_method = send_project_join_request_approval_email
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


class BRCNewProjectUserRunner(NewProjectUserRunner):
    """A concrete class that performs processing when a User is
    newly-associated with a Project, including additional BRC-specific
    handling."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _run_extra_steps(self):
        """Run extra processing steps.
            1. For Vector projects, add the user to a designated project
            on the primary cluster.
        """
        if self._is_vector_project():
            add_vector_user_to_designated_savio_project(self._user_obj)

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

    def _run_extra_steps(self):
        """Run extra processing steps.
            1. For external users who require a host user, set it.
            2. For Recharge projects, set a BillingActivity for usage.
        """
        if needs_host(self._user_obj):
            self._set_host_user()
        if self._is_recharge_project():
            self._set_recharge_billing_activity()

    def _is_recharge_project(self):
        """Return whether the Project has a Recharge allowance."""
        computing_allowance_interface = ComputingAllowanceInterface()
        computing_allowance = \
            computing_allowance_interface.allowance_from_project(
                self._project_obj)
        computing_allowance = ComputingAllowance(computing_allowance)
        return computing_allowance.is_recharge()

    def _set_host_user(self):
        """Determine and set a host_user in the ProjectUser's
        UserProfile if possible. If not, raise an exception."""
        host_user = None
        if self._source == NewProjectUserSource.JOINED:
            join_requests = ProjectUserJoinRequest.objects.filter(
                project_user=self._project_user_obj, host_user__isnull=False)
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

    def _set_recharge_billing_activity(self):
        """TODO"""
        pass


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
