from decimal import Decimal
from unittest.mock import patch

from django.core import mail

from coldfront.api.statistics.utils import create_project_allocation
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AllocationUser
from coldfront.core.allocation.models import AllocationUserAttribute
from coldfront.core.allocation.models import AllocationUserStatusChoice
from coldfront.core.allocation.models import ClusterAccessRequest
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.utils_.project_cluster_access_request_runner import ProjectClusterAccessRequestRunner
from coldfront.core.utils.email.email_strategy import EnqueueEmailStrategy
from coldfront.core.utils.tests.test_base import TestBase


def raise_exception(*args, **kwargs):
    """Raise an exception."""
    raise Exception('Test exception.')


class TestProjectClusterAccessRequestRunner(TestBase):
    """A class for testing ProjectClusterAccessRequestRunner."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)

        # Create a Project with a computing allowance.
        self.project = self.create_active_project_with_pi(
            'fc_project', self.user)
        accounting_allocation_objects = create_project_allocation(
            self.project, Decimal('0.00'))
        self.allocation = accounting_allocation_objects.allocation

        self.project_user = self.project.projectuser_set.get(user=self.user)

    def _assert_post_state(self):
        """Assert that the relevant objects have the expected state,
        assuming that the runner has run successfully."""
        active_allocation_users = AllocationUser.objects.filter(
            allocation=self.allocation, user=self.user, status__name='Active')
        self.assertEqual(active_allocation_users.count(), 1)

        pending_add_allocation_user_attributes = \
            AllocationUserAttribute.objects.filter(
                allocation_attribute_type__name='Cluster Account Status',
                allocation_user__allocation=self.allocation,
                allocation_user__user=self.user,
                value='Pending - Add')
        self.assertEqual(pending_add_allocation_user_attributes.count(), 1)

        cluster_access_requests = ClusterAccessRequest.objects.filter(
            allocation_user__allocation=self.allocation,
            allocation_user__user=self.user)
        self.assertEqual(cluster_access_requests.count(), 1)

    def _assert_pre_state(self):
        """Assert that the relevant objects have the expected state,
        assuming that the runner has either not run or not run
        successfully."""
        active_allocation_users = AllocationUser.objects.filter(
            allocation=self.allocation, user=self.user, status__name='Active')
        self.assertFalse(active_allocation_users.exists())

        pending_add_allocation_user_attributes = \
            AllocationUserAttribute.objects.filter(
                allocation_attribute_type__name='Cluster Account Status',
                allocation_user__allocation=self.allocation,
                allocation_user__user=self.user,
                value='Pending - Add')
        self.assertFalse(pending_add_allocation_user_attributes.exists())

        cluster_access_requests = ClusterAccessRequest.objects.filter(
            allocation_user__allocation=self.allocation,
            allocation_user__user=self.user)
        self.assertFalse(cluster_access_requests.exists())

    def test_asserts_no_existing_cluster_access(self):
        """Test that the runner asserts that the User does not have a
        pending or active AllocationUserAttribute with type 'Cluster
        Account Status'."""
        removed_status = AllocationUserStatusChoice.objects.get(name='Removed')
        allocation_user = AllocationUser.objects.create(
            allocation=self.allocation, user=self.user, status=removed_status)
        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Cluster Account Status')
        allocation_user_attribute = AllocationUserAttribute.objects.create(
            allocation_attribute_type=allocation_attribute_type,
            allocation=self.allocation,
            allocation_user=allocation_user,
            value='')

        self._assert_pre_state()

        runner = ProjectClusterAccessRequestRunner(self.project_user)
        for invalid_value in ('Pending - Add', 'Processing', 'Active'):
            allocation_user_attribute.value = invalid_value
            allocation_user_attribute.save()
            with self.assertRaises(AssertionError) as cm:
                runner.run()
            self.assertIn(
                'already has pending or active access', str(cm.exception))

        allocation_user_attribute.value = ''
        allocation_user_attribute.save()

        self._assert_pre_state()

    def test_asserts_project_user_active(self):
        """Test that the runner asserts that the input ProjectUser has
        the 'Active' status."""
        active_status = ProjectUserStatusChoice.objects.get(name='Active')
        self.assertEqual(self.project_user.status, active_status)
        ProjectClusterAccessRequestRunner(self.project_user)

        other_statuses = ProjectUserStatusChoice.objects.exclude(
            pk=active_status.pk)
        self.assertTrue(other_statuses.exists())
        for status in other_statuses:
            self.project_user.status = status
            self.project_user.save()
            with self.assertRaises(AssertionError):
                ProjectClusterAccessRequestRunner(self.project_user)

    def test_email_strategy_default(self):
        """Test that, if no EmailStrategy is provided to the runner, it
        defaults to using SendEmailStrategy (i.e., it sends emails
        immediately)."""
        self.assertEqual(len(mail.outbox), 0)

        runner = ProjectClusterAccessRequestRunner(self.project_user)
        runner.run()

        self.assertEqual(len(mail.outbox), 1)

    def test_email_strategy_enqueue(self):
        """Test that, if the EnqueueEmailStrategy is provided to the
        runner, it does not send emails, but enqueues them for later
        sending."""
        self.assertEqual(len(mail.outbox), 0)

        email_strategy = EnqueueEmailStrategy()
        runner = ProjectClusterAccessRequestRunner(
            self.project_user, email_strategy=email_strategy)
        runner.run()

        self.assertEqual(len(mail.outbox), 0)

        self.assertEqual(len(email_strategy.get_queue()), 1)
        email_strategy.send_queued_emails()

        self.assertEqual(len(mail.outbox), 1)

    def test_failure(self):
        """Test that, when an exception is raised inside the
        transaction, changes made so far are rolled back, and no emails
        are sent or queued for sending."""
        self.assertEqual(len(mail.outbox), 0)

        self._assert_pre_state()

        email_strategy = EnqueueEmailStrategy()
        with patch.object(
                ProjectClusterAccessRequestRunner,
                '_create_cluster_access_request', raise_exception):
            runner = ProjectClusterAccessRequestRunner(
                self.project_user, email_strategy=email_strategy)
            with self.assertRaises(Exception) as cm:
                runner.run()
            self.assertEqual(str(cm.exception), 'Test exception.')

        self._assert_pre_state()
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(len(email_strategy.get_queue()), 0)

    def test_requires_project_with_compute_allocation(self):
        """Test that the runner raises an exception if the ProjectUser's
        Project does not have an Allocation to a computing Resource."""
        self.allocation.delete()
        with self.assertRaises(Exception):
            ProjectClusterAccessRequestRunner(self.project_user)

    def test_success_previously_existent_objects(self):
        """Test that the runner creates and updates expected database
        objects when some objects previously existed."""
        removed_status = AllocationUserStatusChoice.objects.get(name='Removed')
        allocation_user = AllocationUser.objects.create(
            allocation=self.allocation, user=self.user, status=removed_status)
        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Cluster Account Status')
        allocation_user_attribute = AllocationUserAttribute.objects.create(
            allocation_attribute_type=allocation_attribute_type,
            allocation=self.allocation,
            allocation_user=allocation_user,
            value='Denied')

        self._assert_pre_state()

        runner = ProjectClusterAccessRequestRunner(self.project_user)
        runner.run()

        self._assert_post_state()

        allocation_user.refresh_from_db()
        self.assertEqual(allocation_user.status.name, 'Active')
        allocation_user_attribute.refresh_from_db()
        self.assertEqual(allocation_user_attribute.value, 'Pending - Add')

    def test_success_previously_nonexistent_objects(self):
        """Test that the runner creates and updates expected database
        objects when some objects previously did not exist."""
        self._assert_pre_state()

        allocation_users = AllocationUser.objects.filter(
            allocation=self.allocation, user=self.user)
        self.assertFalse(allocation_users.exists())

        allocation_user_attributes = \
            AllocationUserAttribute.objects.filter(
                allocation_attribute_type__name='Cluster Account Status',
                allocation_user__allocation=self.allocation,
                allocation_user__user=self.user)
        self.assertFalse(allocation_user_attributes.exists())

        runner = ProjectClusterAccessRequestRunner(self.project_user)
        runner.run()

        self._assert_post_state()
