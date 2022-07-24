from decimal import Decimal
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail

from coldfront.api.statistics.utils import create_project_allocation, \
    create_user_project_allocation
from coldfront.core.allocation.models import ClusterAccessRequest, \
    ClusterAccessRequestStatusChoice, AllocationAttributeType, \
    AllocationUserAttribute
from coldfront.core.allocation.utils_.cluster_access_utils import \
    ClusterAccessRequestCompleteRunner, \
    ClusterAccessRequestDenialRunner
from coldfront.core.project.models import ProjectStatusChoice, \
    ProjectUserStatusChoice, ProjectUserRoleChoice, ProjectUser, Project
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import TestBase


def raise_exception(*args, **kwargs):
    """Raise an exception."""
    raise Exception('Test exception.')


class TestClusterAccessRunnersBase(TestBase):
    """A base testing class for cluster access runners."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

        # Create User
        self.user0 = User.objects.create(
            username='user0', email=f'user0@nonexistent.com')

        self.manager = User.objects.create(
            username='manager', email='manager@nonexistent.com')

        # Create Projects and associate Users with them.
        project_status = ProjectStatusChoice.objects.get(name='Active')
        project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')
        manager_role = ProjectUserRoleChoice.objects.get(name='Manager')
        user_role = ProjectUserRoleChoice.objects.get(name='User')

        # Create a Project and ProjectUsers.
        self.project0 = Project.objects.create(
            name='project0', status=project_status)

        ProjectUser.objects.create(
            user=self.user0, project=self.project0,
            role=user_role, status=project_user_status)
        ProjectUser.objects.create(
            user=self.manager, project=self.project0,
            role=manager_role, status=project_user_status)

        # Create a compute allocation for the Project.
        allocation = Decimal('1000.00')
        self.alloc_obj = create_project_allocation(self.project0, allocation)

        # Create a compute allocation for each User on the Project.
        self.alloc_user_obj = create_user_project_allocation(
            self.user0, self.project0, allocation / 2)
        self.alloc_user = self.alloc_user_obj.allocation_user

        # Create ClusterAccessRequest
        self.request_obj = ClusterAccessRequest.objects.create(
            allocation_user=self.alloc_user,
            status=ClusterAccessRequestStatusChoice.objects.get(
                name='Pending - Add'),
            request_time=utc_now_offset_aware())

        self._module = 'coldfront.core.allocation.utils_.cluster_access_utils'

    def _get_cluster_account_status_attr(self):
        cluster_account_status = \
            AllocationAttributeType.objects.get(name='Cluster Account Status')
        cluster_access_attribute = \
            AllocationUserAttribute.objects.filter(
                allocation_attribute_type=cluster_account_status,
                allocation=self.alloc_user.allocation,
                allocation_user=self.alloc_user)
        return cluster_access_attribute


class TestClusterAccessRequestCompleteRunner(TestClusterAccessRunnersBase):
    """A testing class for ClusterAccessRequestCompleteRunner."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.request_obj.status = \
            ClusterAccessRequestStatusChoice.objects.get(name='Active')
        self.request_obj.completion_time = utc_now_offset_aware()
        self.request_obj.save()
        
        self.runner = ClusterAccessRequestCompleteRunner(self.request_obj)

        self.new_username = 'new_username'
        self.cluster_uid = '1234'

        self.alloc_user_obj.allocation_user_attribute.value = Decimal('0.00')
        self.alloc_user_obj.allocation_user_attribute.save()

    def _assert_emails_sent(self):
        email_body = [f'now has access to the project {self.project0.name}.',
                      f'supercluster username is - {self.new_username}',
                      f'If this is the first time you are accessing',
                      f'start with the below Logging In page:']

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]

        self.assertIn('Cluster Access Activated', email.subject)
        for section in email_body:
            self.assertIn(section, email.body)
        self.assertEqual(email.to, [self.user0.email])
        self.assertEqual(email.cc, [self.manager.email])
        self.assertEqual(settings.EMAIL_SENDER, email.from_email)

    def _refresh_objects(self):
        """Refresh relevant objects from db."""
        self.request_obj.refresh_from_db()
        self.user0.refresh_from_db()
        self.alloc_obj.allocation.refresh_from_db()
        self.alloc_user_obj.allocation_user.refresh_from_db()
        self.alloc_user_obj.allocation_user_attribute.refresh_from_db()

    def _assert_pre_state(self):
        """Assert that the relevant objects have the expected state,
        assuming that the runner has either not run or not run
        successfully."""
        self._refresh_objects()
        # self.assertEqual(self.request_obj.status.name, 'Pending - Add')
        self.assertIsNone(self.user0.userprofile.cluster_uid)
        self.assertEqual(self.user0.username, 'user0')
        # self.assertIsNone(self.request_obj.completion_time)
        self.assertNotEqual(self.alloc_user_obj.allocation_user_attribute.value,
                            self.alloc_obj.allocation_attribute.value)
        self.assertFalse(self._get_cluster_account_status_attr().exists())

    def _assert_post_state(self):
        """Assert that the relevant objects have the expected state,
        assuming that the runner has run successfully."""
        self._refresh_objects()
        self.assertEqual(self.user0.userprofile.cluster_uid, self.cluster_uid)
        self.assertEqual(self.user0.username, self.new_username)
        self.assertEqual(self.alloc_user_obj.allocation_user_attribute.value,
                         self.alloc_obj.allocation_attribute.value)
        self.assertTrue(self._get_cluster_account_status_attr().exists())
        self.assertEqual(self._get_cluster_account_status_attr().first().value,
                         'Active')

    def test_success(self):
        """Test that the request status is set to Active, Cluster Account
        Status AllocationUserAttribute is set to Active, completion time
        is set, cluster_uid is set, new username is set, user SUs are set to
        allocation's SUs, emails are sent, and log messages are written."""
        self.assertEqual(len(mail.outbox), 0)
        self._assert_pre_state()

        with self.assertLogs(self._module, 'INFO') as cm:
            self.runner.run(self.new_username,
                            self.cluster_uid)

        self._assert_post_state()

        self.assertGreater(len(cm.output), 0)
        self._assert_emails_sent()

        self.assertFalse(self.runner.get_warning_messages())

    def test_exception_inside_transaction_rollback(self):
        """Test that, when an exception is raised inside the
         transaction, changes made so far are rolled back."""
        self.assertEqual(len(mail.outbox), 0)
        self._assert_pre_state()

        with patch.object(
                ClusterAccessRequestCompleteRunner,
                '_set_cluster_uid',
                raise_exception):
            with self.assertRaises(Exception) as cm:
                self.runner.run(self.new_username,
                                self.cluster_uid)
            self.assertEqual(str(cm.exception), 'Test exception.')

        self._assert_pre_state()
        self.assertEqual(len(mail.outbox), 0)

    def test_email_failure_no_rollback(self):
        """Test that, when an exception is raised when attempting to
        send an email, changes made so far are not rolled back because
        such an exception is caught."""
        self.assertEqual(len(mail.outbox), 0)
        self._assert_pre_state()

        with patch.object(
                ClusterAccessRequestCompleteRunner,
                '_send_complete_emails',
                raise_exception):
            with self.assertLogs(self._module, 'INFO') as log_cm:
                self.runner.run(self.new_username,
                                self.cluster_uid)

        self._assert_post_state()

        self.assertGreater(len(log_cm.output), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_exception_outside_transaction_no_rollback(self):
        """Test that, when an exception is raised outside the
        transaction, changes made so far are not rolled back."""
        self.assertEqual(len(mail.outbox), 0)
        self._assert_pre_state()

        with patch.object(
                ClusterAccessRequestCompleteRunner,
                '_send_emails_safe',
                raise_exception):
            with self.assertLogs(self._module, 'INFO') as log_cm:
                with self.assertRaises(Exception) as exc_cm:
                    self.runner.run(self.new_username,
                                    self.cluster_uid)
            self.assertEqual(str(exc_cm.exception), 'Test exception.')

        self._assert_post_state()

        self.assertGreater(len(log_cm.output), 0)
        self.assertEqual(len(mail.outbox), 0)


class TestClusterAccessRequestDenialRunner(TestClusterAccessRunnersBase):
    """A testing class for ClusterAccessRequestDenialRunner."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.request_obj.status = \
            ClusterAccessRequestStatusChoice.objects.get(name='Denied')
        self.request_obj.completion_time = utc_now_offset_aware()
        self.request_obj.save()
        
        self.runner = ClusterAccessRequestDenialRunner(self.request_obj)

    def _assert_emails_sent(self):
        email_body = [f'access request under project {self.project0.name}',
                      f'and allocation {self.alloc_obj.allocation.pk} '
                      f'has been denied.']

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]

        self.assertIn('Cluster Access Denied', email.subject)
        for section in email_body:
            self.assertIn(section, email.body)
        self.assertEqual(email.to, [self.user0.email])
        self.assertEqual(email.cc, [self.manager.email])
        self.assertEqual(settings.EMAIL_SENDER, email.from_email)

    def _assert_pre_state(self):
        """Assert that the relevant objects have the expected state,
        assuming that the runner has either not run or not run
        successfully."""
        self.request_obj.refresh_from_db()
        # self.assertIsNone(self.request_obj.completion_time)
        # self.assertEqual(self.request_obj.status.name, 'Pending - Add')
        self.assertFalse(self._get_cluster_account_status_attr().exists())

    def _assert_post_state(self):
        """Assert that the relevant objects have the expected state,
        assuming that the runner has run successfully."""
        self.request_obj.refresh_from_db()
        self.assertTrue(self._get_cluster_account_status_attr().exists())
        self.assertEqual(self._get_cluster_account_status_attr().first().value,
                         'Denied')

    def test_success(self):
        """Test that the request status is set to Denied, Cluster Account
        Status AllocationUserAttribute is set to Denied, completion time
        is set, emails are sent, and log messages are written."""
        self.assertEqual(len(mail.outbox), 0)
        self._assert_pre_state()

        with self.assertLogs(self._module, 'INFO') as cm:
            self.runner.run()

        self._assert_post_state()

        self.assertGreater(len(cm.output), 0)
        self._assert_emails_sent()

        self.assertFalse(self.runner.get_warning_messages())

    def test_exception_inside_transaction_rollback(self):
        """Test that, when an exception is raised inside the
         transaction, changes made so far are rolled back."""
        self.assertEqual(len(mail.outbox), 0)
        self._assert_pre_state()

        with patch.object(
                ClusterAccessRequestDenialRunner,
                '_deny_cluster_access_attribute',
                raise_exception):
            with self.assertRaises(Exception) as cm:
                self.runner.run()
            self.assertEqual(str(cm.exception), 'Test exception.')

        self._assert_pre_state()
        self.assertEqual(len(mail.outbox), 0)

    def test_email_failure_no_rollback(self):
        """Test that, when an exception is raised when attempting to
        send an email, changes made so far are not rolled back because
        such an exception is caught."""
        self.assertEqual(len(mail.outbox), 0)
        self._assert_pre_state()

        with patch.object(
                ClusterAccessRequestDenialRunner,
                '_send_denial_emails',
                raise_exception):
            with self.assertLogs(self._module, 'INFO') as log_cm:
                self.runner.run()

        self._assert_post_state()

        self.assertGreater(len(log_cm.output), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_exception_outside_transaction_no_rollback(self):
        """Test that, when an exception is raised outside the
        transaction, changes made so far are not rolled back."""
        self.assertEqual(len(mail.outbox), 0)
        self._assert_pre_state()

        with patch.object(
                ClusterAccessRequestDenialRunner,
                '_send_emails_safe',
                raise_exception):
            with self.assertLogs(self._module, 'INFO') as log_cm:
                with self.assertRaises(Exception) as exc_cm:
                    self.runner.run()
            self.assertEqual(str(exc_cm.exception), 'Test exception.')

        self._assert_post_state()

        self.assertGreater(len(log_cm.output), 0)
        self.assertEqual(len(mail.outbox), 0)
