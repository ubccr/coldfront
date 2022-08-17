from decimal import Decimal
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail

from coldfront.api.statistics.utils import create_project_allocation
from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AllocationUser
from coldfront.core.allocation.models import AllocationUserAttribute
from coldfront.core.allocation.models import AllocationUserStatusChoice
from coldfront.core.allocation.models import ClusterAccessRequest
from coldfront.core.allocation.utils_.cluster_access_utils import ClusterAccessRequestRunnerValidationError
from coldfront.core.allocation.utils_.cluster_access_utils import send_new_cluster_access_request_notification_email
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.utils import send_added_to_project_notification_email
from coldfront.core.project.utils import send_project_join_request_approval_email
from coldfront.core.project.utils_.new_project_user_utils import BRCNewProjectUserRunner
from coldfront.core.project.utils_.new_project_user_utils import LRCNewProjectUserRunner
from coldfront.core.project.utils_.new_project_user_utils import NewProjectUserRunner
from coldfront.core.project.utils_.new_project_user_utils import NewProjectUserRunnerFactory
from coldfront.core.project.utils_.new_project_user_utils import NewProjectUserSource
from coldfront.core.project.models import ProjectUserJoinRequest
from coldfront.core.resource.models import Resource
from coldfront.core.user.models import UserProfile
from coldfront.core.utils.email.email_strategy import EnqueueEmailStrategy
from coldfront.core.utils.tests.test_base import enable_deployment
from coldfront.core.utils.tests.test_base import TestBase


def raise_exception(*args, **kwargs):
    """Raise an exception."""
    raise Exception('Test exception.')


class TestNewProjectUserRunner(TestBase):
    """A class for testing NewProjectUserRunner."""

    def test_not_instantiatable(self):
        """Test that an instance of the class may not be
        instantiated."""
        with self.assertRaises(TypeError) as cm:
            NewProjectUserRunner(None, None)
        self.assertIn('Can\'t instantiate', str(cm.exception))


class TestRunnerBase(TestBase):
    """A base class for testing NewProjectUserRunner classes."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)

        # Create a Project with a computing allowance, along with an 'Active'
        # ProjectUser.
        self.project = self.create_active_project_with_pi(
            'fc_project', self.user)
        accounting_allocation_objects = create_project_allocation(
            self.project, Decimal('0.00'))
        self.allocation = accounting_allocation_objects.allocation
        self.project_user = self.project.projectuser_set.get(user=self.user)


class TestNewProjectUserRunnerFactory(TestRunnerBase):
    """A class for testing NewProjectUserRunnerFactory."""

    def test_creates_expected_runner(self):
        """Test that the factory creates the expected runner, based on
        feature flags."""
        factory = NewProjectUserRunnerFactory()
        with enable_deployment('BRC'):
            runner = factory.get_runner(
                self.project_user, NewProjectUserSource.ADDED)
            self.assertIsInstance(runner, BRCNewProjectUserRunner)
        with enable_deployment('LRC'):
            runner = factory.get_runner(
                self.project_user, NewProjectUserSource.JOINED)
            self.assertIsInstance(runner, LRCNewProjectUserRunner)


class TestCommonRunnerMixin(object):
    """A mixin for testing functionality common to all concrete runner
    classes."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self._runner_factory = NewProjectUserRunnerFactory()

    def _assert_post_state(self):
        """Assert that the relevant objects have the expected state,
        assuming that the runner has run successfully."""
        active_allocation_users = AllocationUser.objects.filter(
            allocation=self.allocation, user=self.user, status__name='Active')
        self.assertEqual(active_allocation_users.count(), 1)

        cluster_access_requests = ClusterAccessRequest.objects.filter(
            allocation_user__user=self.user, status__name='Pending - Add')
        self.assertEqual(cluster_access_requests.count(), 1)

    def _assert_pre_state(self):
        """Assert that the relevant objects have the expected state,
        assuming that the runner has either not run or not run
        successfully."""
        active_allocation_users = AllocationUser.objects.filter(
            allocation=self.allocation, user=self.user, status__name='Active')
        self.assertEqual(active_allocation_users.count(), 0)

        cluster_access_requests = ClusterAccessRequest.objects.filter(
            allocation_user__user=self.user)
        self.assertFalse(cluster_access_requests.exists())

    def _rollback_changes(self):
        """Roll back changes made by the runner so that it may be run
        again."""
        AllocationUser.objects.filter(
            allocation=self.allocation, user=self.project_user.user).delete()

    def test_cluster_access_not_requested_based_on_source(self):
        """Test that no attempt is made to request cluster access for
        particular NewProjectUserSources."""
        excluded_sources = {
            NewProjectUserSource.NEW_PROJECT_NON_REQUESTER_PI,
            NewProjectUserSource.ALLOCATION_RENEWAL_NON_REQUESTER_PI,
        }
        for source in NewProjectUserSource:
            email_strategy = EnqueueEmailStrategy()
            args = (self.project_user, source)
            kwargs = {'email_strategy': email_strategy}
            with enable_deployment(self._deployment_name):
                _class = self._runner_factory.get_runner(
                    *args, **kwargs).__class__
                with patch.object(
                        _class, '_request_cluster_access', raise_exception):
                    runner = self._runner_factory.get_runner(*args, **kwargs)
                    if source not in excluded_sources:
                        with self.assertRaises(Exception) as cm:
                            runner.run()
                        self.assertEqual(str(cm.exception), 'Test exception.')
                    else:
                        runner.run()
                        self._rollback_changes()

    def test_email_strategy_default(self):
        """Test that, if no EmailStrategy is provided to the runner, it
        defaults to using SendEmailStrategy (i.e., it sends emails
        immediately)."""
        self.assertEqual(len(mail.outbox), 0)

        with enable_deployment(self._deployment_name):
            runner = self._runner_factory.get_runner(
                self.project_user, NewProjectUserSource.ADDED)
        runner.run()

        self.assertEqual(len(mail.outbox), 2)

        # Additionally, test that the correct email is sent for the source.
        added_email_found = False
        for email in mail.outbox:
            if f'Added to Project {self.project.name}' in email.subject:
                added_email_found = True
                break
        self.assertTrue(added_email_found)

    def test_email_strategy_enqueue(self):
        """Test that if the EnqueueEmailStrategy is provided to the
        runner, it does not send emails, but enqueues them for later
        sending."""
        self.assertEqual(len(mail.outbox), 0)

        email_strategy = EnqueueEmailStrategy()
        with enable_deployment(self._deployment_name):
            runner = self._runner_factory.get_runner(
                self.project_user, NewProjectUserSource.JOINED,
                email_strategy=email_strategy)
        runner.run()

        self.assertEqual(len(mail.outbox), 0)

        self.assertEqual(len(email_strategy.get_queue()), 2)
        email_strategy.send_queued_emails()

        self.assertEqual(len(mail.outbox), 2)

        # Additionally, test that the correct email is sent for the source.
        join_approval_email_found = False
        for email in mail.outbox:
            if f'Join {self.project.name} Approved' in email.subject:
                join_approval_email_found = True
                break
        self.assertTrue(join_approval_email_found)

    def test_emails_conditionally_sent_based_on_source(self):
        """Test that emails about the new project user (excluding those
        about cluster access) are only sent for particular
        NewProjectUserSources."""
        expected_email_methods_by_source = {
            NewProjectUserSource.ADDED: (
                send_added_to_project_notification_email),
            NewProjectUserSource.JOINED: (
                send_project_join_request_approval_email),
            NewProjectUserSource.AUTO_ADDED: (
                send_added_to_project_notification_email),
        }
        cluster_access_email_method = \
            send_new_cluster_access_request_notification_email
        for source in NewProjectUserSource:
            email_strategy = EnqueueEmailStrategy()
            with enable_deployment(self._deployment_name):
                runner = self._runner_factory.get_runner(
                    self.project_user, source, email_strategy=email_strategy)
            runner.run()

            self.assertEqual(len(mail.outbox), 0)

            queued_emails = email_strategy.get_queue()
            if source in expected_email_methods_by_source:
                # If an email is expected, assert that it is the correct one,
                # ignoring any email about cluster access.
                expected_method = expected_email_methods_by_source[source]
                match_found = False
                while queued_emails:
                    item = queued_emails.popleft()
                    email_method = item[0]
                    if email_method == cluster_access_email_method:
                        continue
                    if email_method == expected_method:
                        match_found = True
                        break
                self.assertTrue(match_found)
            else:
                # Otherwise, assert that no email is sent, ignoring any email
                # about cluster access.
                unexpected_found = False
                while queued_emails:
                    item = queued_emails.popleft()
                    email_method = item[0]
                    if email_method == cluster_access_email_method:
                        continue
                    else:
                        unexpected_found = True
                        break
                self.assertFalse(unexpected_found)

            self._rollback_changes()

    def test_failure(self):
        """Test that, when an exception is raised inside the
        transaction, changes made so far are rolled back. Test that only
        particular emails are sent for particular EmailStrategy
        instances."""
        self.assertEqual(len(mail.outbox), 0)
        self._assert_pre_state()

        args = (self.project_user, NewProjectUserSource.ADDED)
        email_strategy = EnqueueEmailStrategy()

        with enable_deployment(self._deployment_name):
            _class = self._runner_factory.get_runner(*args).__class__
            with patch.object(_class, '_run_extra_steps', raise_exception):
                runner = self._runner_factory.get_runner(
                    *args, email_strategy=email_strategy)
                with self.assertRaises(Exception) as cm:
                    runner.run()
                self.assertEqual(str(cm.exception), 'Test exception.')

        self._assert_pre_state()

        # When using EnqueueEmailStrategy, an email about a new cluster access
        # request should be queued, but not sent.
        self.assertEqual(len(mail.outbox), 0)
        queue = email_strategy.get_queue()
        self.assertEqual(len(queue), 1)
        email_method, _, _ = queue.popleft()
        self.assertEqual(
            email_method, send_new_cluster_access_request_notification_email)

        with patch.object(_class, '_run_extra_steps', raise_exception):
            with enable_deployment(self._deployment_name):
                runner = self._runner_factory.get_runner(*args)
            with self.assertRaises(Exception) as cm:
                runner.run()
            self.assertEqual(str(cm.exception), 'Test exception.')

        self._assert_pre_state()

        # When using SendEmailStrategy, an email about a new cluster access
        # request should be sent, even though the enclosing transaction failed.
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn('New Cluster Access Request', email.subject)

    def test_preexisting_cluster_access_allowed_based_on_source(self):
        """Test that, when the user already has access to the cluster,
        an exception is not raised for particular
        NewProjectUserSources."""
        allowed_sources = {
            NewProjectUserSource.NEW_PROJECT_REQUESTER,
            NewProjectUserSource.NEW_PROJECT_NON_REQUESTER_PI,
            NewProjectUserSource.ALLOCATION_RENEWAL_REQUESTER,
            NewProjectUserSource.ALLOCATION_RENEWAL_NON_REQUESTER_PI,
            NewProjectUserSource.AUTO_ADDED,
        }

        active_status = AllocationUserStatusChoice.objects.get(name='Active')
        allocation_user = AllocationUser.objects.create(
            allocation=self.allocation, user=self.user, status=active_status)
        AllocationUserAttribute.objects.create(
            allocation_attribute_type=AllocationAttributeType.objects.get(
                name='Cluster Account Status'),
            allocation=self.allocation,
            allocation_user=allocation_user,
            value='Pending - Add')

        expected_exception = ClusterAccessRequestRunnerValidationError
        for source in NewProjectUserSource:
            email_strategy = EnqueueEmailStrategy()
            args = (self.project_user, source)
            kwargs = {'email_strategy': email_strategy}
            with enable_deployment(self._deployment_name):
                runner = self._runner_factory.get_runner(*args, **kwargs)
                if source not in allowed_sources:
                    with self.assertRaises(expected_exception):
                        runner.run()
                else:
                    runner.run()

    def test_success(self):
        """Test that the runner performs expected processing."""
        self._assert_pre_state()

        with enable_deployment(self._deployment_name):
            runner = self._runner_factory.get_runner(
                self.project_user, NewProjectUserSource.ADDED)
        runner.run()

        self._assert_post_state()

    def test_updates_allocation_user_if_existent(self):
        """Test that the runner updates an AllocationUser object if it
        already exists."""
        self._assert_pre_state()

        removed_status = AllocationUserStatusChoice.objects.get(name='Removed')
        allocation_user = AllocationUser.objects.create(
            allocation=self.allocation, user=self.user, status=removed_status)

        with enable_deployment(self._deployment_name):
            runner = self._runner_factory.get_runner(
                self.project_user, NewProjectUserSource.ADDED)
        runner.run()

        allocation_user.refresh_from_db()
        active_status = AllocationUserStatusChoice.objects.get(name='Active')
        self.assertEqual(allocation_user.status, active_status)

        self._assert_post_state()


class TestBRCNewProjectUserRunner(TestCommonRunnerMixin, TestRunnerBase):
    """A class for testing BRCNewProjectUserRunner."""

    @enable_deployment('BRC')
    def setUp(self):
        """Set up test data."""
        super().setUp()
        self._deployment_name = 'BRC'

    @enable_deployment('BRC')
    def test_add_vector_user_to_designated_savio_project_failure(self):
        """Test that, if adding a Vector user to the designated Savio
        project on Savio fails, the already-made changes are not rolled
        back."""
        # Create a PI.
        pi = User.objects.create(username='pi0', email='pi0@nonexistent.com')
        user_profile = UserProfile.objects.get(user=pi)
        user_profile.is_pi = True
        user_profile.save()

        savio_project_name = settings.SAVIO_PROJECT_FOR_VECTOR_USERS
        savio_project = self.create_active_project_with_pi(
            savio_project_name, pi)
        savio_project_allocation = create_project_allocation(
            savio_project, Decimal('0.00')).allocation

        vector_project = self.create_active_project_with_pi(
            'vector_project', self.user)
        vector_project_allocation = Allocation.objects.create(
            project=vector_project, status=savio_project_allocation.status)
        vector_project_allocation.resources.add(
            Resource.objects.get(name='Vector Compute'))
        project_user = vector_project.projectuser_set.get(user=self.user)

        self.assertEqual(len(mail.outbox), 0)

        method_to_patch = (
            'coldfront.core.project.utils_.new_project_user_utils.'
            'add_vector_user_to_designated_savio_project')
        with patch(method_to_patch) as patched_method:
            patched_method.side_effect = raise_exception
            runner = self._runner_factory.get_runner(
                project_user, NewProjectUserSource.ADDED)
            runner.run()

        self.assertIn(
            'Failed to automatically add', runner.get_warning_messages()[0])

        # There should be one ClusterAccessRequest, for the Vector project.
        cluster_access_requests = ClusterAccessRequest.objects.filter(
            allocation_user__user=self.user)
        self.assertEqual(cluster_access_requests.count(), 1)
        vector_request = cluster_access_requests.get(
            allocation_user__allocation=vector_project_allocation)
        self.assertEqual(vector_request.status.name, 'Pending - Add')

        self.assertEqual(len(mail.outbox), 2)

    @enable_deployment('BRC')
    def test_add_vector_user_to_designated_savio_project_success(self):
        """Test that, for a Vector project, the user is also added to
        the designated project on Savio."""
        # Create a PI.
        pi = User.objects.create(username='pi0', email='pi0@nonexistent.com')
        user_profile = UserProfile.objects.get(user=pi)
        user_profile.is_pi = True
        user_profile.save()

        savio_project_name = settings.SAVIO_PROJECT_FOR_VECTOR_USERS
        savio_project = self.create_active_project_with_pi(
            savio_project_name, pi)
        savio_project_allocation = create_project_allocation(
            savio_project, Decimal('0.00')).allocation

        vector_project = self.create_active_project_with_pi(
            'vector_project', self.user)
        vector_project_allocation = Allocation.objects.create(
            project=vector_project, status=savio_project_allocation.status)
        vector_project_allocation.resources.add(
            Resource.objects.get(name='Vector Compute'))
        project_user = vector_project.projectuser_set.get(user=self.user)

        self.assertEqual(len(mail.outbox), 0)

        runner = self._runner_factory.get_runner(
            project_user, NewProjectUserSource.ADDED)
        runner.run()

        # There should be two ClusterAccessRequests: one for the Vector
        # project, and one for the Savio project.
        cluster_access_requests = ClusterAccessRequest.objects.filter(
            allocation_user__user=self.user)
        self.assertEqual(cluster_access_requests.count(), 2)
        savio_request = cluster_access_requests.get(
            allocation_user__allocation=savio_project_allocation)
        self.assertEqual(savio_request.status.name, 'Pending - Add')
        vector_request = cluster_access_requests.get(
            allocation_user__allocation=vector_project_allocation)
        self.assertEqual(vector_request.status.name, 'Pending - Add')

        self.assertEqual(len(mail.outbox), 4)


class TestLRCNewProjectUserRunner(TestCommonRunnerMixin, TestRunnerBase):
    """A class for testing LRCNewProjectUserRunner."""

    @enable_deployment('LRC')
    def setUp(self):
        """Set up test data."""
        super().setUp()
        self._deployment_name = 'LRC'
        # Create another PI.
        self.pi = User.objects.create(username='pi0', email='pi0@lbl.gov')
        user_profile = UserProfile.objects.get(user=self.pi)
        user_profile.is_pi = True
        user_profile.save()
        ProjectUser.objects.create(
            project=self.project,
            user=self.pi,
            role=ProjectUserRoleChoice.objects.get(
                name='Principal Investigator'),
            status=ProjectUserStatusChoice.objects.get(name='Active'))

    @enable_deployment('LRC')
    def test_set_host_user_failure(self):
        """Test that, if a host user could cannot be determined, the
        runner raises an exception and rolls back changes made so
        far."""
        # For adds (and joins missing a request), the runner attempts to
        # select an eligible host from the PIs of the Project. Alter the
        # would-be host so that it is no longer eligible.
        self.pi.email = 'pi0@email.com'
        self.pi.save()

        self.assertEqual(len(mail.outbox), 0)

        self._assert_pre_state()

        user_profile = self.user.userprofile
        self.assertIsNone(user_profile.host_user)

        email_strategy = EnqueueEmailStrategy()
        runner = self._runner_factory.get_runner(
            self.project_user, NewProjectUserSource.ADDED,
            email_strategy=email_strategy)
        with self.assertRaises(Exception) as cm:
            runner.run()
        self.assertIn('Failed to determine a host', str(cm.exception))

        user_profile.refresh_from_db()
        self.assertIsNone(user_profile.host_user)

        self._assert_pre_state()

        self.assertEqual(len(mail.outbox), 0)
        queue = email_strategy.get_queue()
        self.assertEqual(len(queue), 1)

    @enable_deployment('LRC')
    def test_set_host_user_for_lbl_employee_success(self):
        """Test that the runner sets the host user for an LBL
        employee to the same user."""
        self.user.email = 'user@lbl.gov'
        self.user.save()

        user_profile = self.user.userprofile
        self.assertIsNone(user_profile.host_user)

        runner = self._runner_factory.get_runner(
            self.project_user, NewProjectUserSource.ADDED)
        runner.run()

        user_profile.refresh_from_db()
        self.assertEqual(user_profile.host_user, self.user)

        self._assert_post_state()

    @enable_deployment('LRC')
    def test_set_host_user_for_non_lbl_employee_from_add_success(self):
        """Test that the runner sets the host user for a non-LBL
        employee when the user was added to the Project."""
        self._assert_pre_state()

        user_profile = self.user.userprofile
        self.assertIsNone(user_profile.host_user)

        runner = self._runner_factory.get_runner(
            self.project_user, NewProjectUserSource.ADDED)
        runner.run()

        user_profile.refresh_from_db()
        self.assertEqual(user_profile.host_user, self.pi)

        self._assert_post_state()

    @enable_deployment('LRC')
    def test_set_host_user_for_non_lbl_employee_from_join_success(self):
        """Test that the runner sets the host user for a non-LBL
        employee when the user joined the Project."""
        self._assert_pre_state()

        user_profile = self.user.userprofile
        self.assertIsNone(user_profile.host_user)

        ProjectUserJoinRequest.objects.create(
            project_user=self.project_user, host_user=self.pi)

        runner = self._runner_factory.get_runner(
            self.project_user, NewProjectUserSource.JOINED)
        runner.run()

        user_profile.refresh_from_db()
        self.assertEqual(user_profile.host_user, self.pi)

        self._assert_post_state()

    @enable_deployment('LRC')
    def test_set_host_user_skipped_if_has_one(self):
        """Test that the runner does not set the host user for an LBL
        employee if it already has one."""
        self.user.email = 'user@lbl.gov'
        self.user.save()

        user_profile = self.user.userprofile
        user_profile.host_user = self.user
        user_profile.save()

        # The method for setting a host user should never be invoked, so an
        # exception should not be raised.
        with patch.object(
                LRCNewProjectUserRunner, '_set_host_user', raise_exception):
            runner = self._runner_factory.get_runner(
                self.project_user, NewProjectUserSource.ADDED)
            runner.run()

        user_profile.refresh_from_db()
        self.assertEqual(user_profile.host_user, self.user)

        self._assert_post_state()
