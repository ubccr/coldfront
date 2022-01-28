from coldfront.api.statistics.utils import create_project_allocation
from coldfront.api.statistics.utils import create_user_project_allocation
from coldfront.api.statistics.utils import get_accounting_allocation_objects
from coldfront.api.statistics.utils import set_project_usage_value
from coldfront.api.statistics.utils import set_project_user_usage_value
from coldfront.core.allocation.models import AllocationAdditionRequest
from coldfront.core.allocation.models import AllocationAdditionRequestStatusChoice
from coldfront.core.allocation.models import AllocationAttribute
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AllocationUser
from coldfront.core.allocation.utils import get_project_compute_allocation
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.utils_.addition_utils import AllocationAdditionProcessingRunner
from coldfront.core.statistics.models import ProjectTransaction
from coldfront.core.statistics.models import ProjectUserTransaction
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import TestBase

from decimal import Decimal
from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail


class TestAllocationAdditionProcessingRunner(TestBase):
    """A class for testing AllocationAdditionProcessingRunner."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)

        self.project = self.create_active_project_with_pi(
            'ac_project', self.user)

        self.other_user = User.objects.create(
            email='other_user@email.com',
            first_name='Other',
            last_name='User',
            username='other_user')
        ProjectUser.objects.create(
            project=self.project, user=self.other_user,
            role=ProjectUserRoleChoice.objects.get(name='User'),
            status=ProjectUserStatusChoice.objects.get(name='Active'))

        # The Project has a total allocation of 100 SUs, with some usage.
        self.pre_allocation = Decimal('100.00')
        self.pre_usage = Decimal('37.50')
        create_project_allocation(self.project, self.pre_allocation)
        set_project_usage_value(self.project, self.pre_usage)

        # One User has a sub-allocation of 75 SUs and has used all of it.
        user_values = (Decimal('75.00'), Decimal('75.00'))
        create_user_project_allocation(self.user, self.project, user_values[0])
        set_project_user_usage_value(
            self.user, self.project, user_values[1])

        # Another User has a sub-allocation of 25 SUs and has used half of it.
        other_user_values = (Decimal('25.00'), Decimal('12.50'))
        create_user_project_allocation(
            self.other_user, self.project, other_user_values[0])
        set_project_user_usage_value(
            self.other_user, self.project, other_user_values[1])

        self.values_by_user = {
            self.user: user_values,
            self.other_user: other_user_values,
        }

        # The request will add 300 SUs.
        self.sus_addition = Decimal('300.00')
        # The Project and all ProjectUsers will have the same allocation after
        # the reset and no usage, regardless of individual differences.
        self.expected_post_sus = (self.pre_allocation -
                                  self.pre_usage +
                                  self.sus_addition)

        self.request_obj = \
            AllocationAdditionRequest.objects.create(
                requester=self.user,
                project=self.project,
                status=AllocationAdditionRequestStatusChoice.objects.get(
                    name='Under Review'),
                num_service_units=self.sus_addition)

    def assert_allocation_service_units_values(self, allocation,
                                               expected_value,
                                               expected_usage):
        """Assert that the given Allocation has an AllocationAttribute
        with type 'Service Units' and the given expected value and the
        given expected usage."""
        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Service Units')
        kwargs = {
            'allocation_attribute_type': allocation_attribute_type,
        }
        attributes = allocation.allocationattribute_set.filter(**kwargs)
        self.assertEqual(attributes.count(), 1)
        attribute = attributes.first()
        self.assertEqual(str(expected_value), attribute.value)
        self.assertEqual(
            expected_usage, attribute.allocationattributeusage.value)

    def assert_allocation_user_service_units_values(self, allocation_user,
                                                    expected_value,
                                                    expected_usage):
        """Assert that the given AllocationUser has an
        AllocationUserAttribute with type 'Service Units' and the given
        expected value and the given expected usage."""
        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Service Units')
        kwargs = {
            'allocation_attribute_type': allocation_attribute_type,
        }
        attributes = allocation_user.allocationuserattribute_set.filter(
            **kwargs)
        self.assertEqual(attributes.count(), 1)
        attribute = attributes.first()
        self.assertEqual(str(expected_value), attribute.value)
        self.assertEqual(
            expected_usage, attribute.allocationuserattributeusage.value)

    def test_pre_existent_accounting_objects_assumed(self):
        """Test that the runner assumes that the Project has an
        Allocation, a 'Service Units' attribute, and an associated
        usage."""
        # Delete the 'Service Units' attribute.
        objects = get_accounting_allocation_objects(self.project)
        objects.allocation_attribute.delete()

        try:
            AllocationAdditionProcessingRunner(
                self.request_obj)
        except AllocationAttribute.DoesNotExist:
            pass
        else:
            self.fail('An exception should have been raised.')

        # Recreate it.
        AllocationAttribute.objects.create(
            allocation_attribute_type=AllocationAttributeType.objects.get(
                name='Service Units'),
            allocation=objects.allocation,
            value=Decimal('100.00'))

        try:
            AllocationAdditionProcessingRunner(
                self.request_obj)
        except AllocationAttribute.DoesNotExist:
            self.fail('An exception should not have been raised.')

    def test_request_status_validated(self):
        """Test that the runner raises an error if the request does not
        have the 'Under Review' status."""
        for status in AllocationAdditionRequestStatusChoice.objects.all():
            self.request_obj.status = status
            self.request_obj.save()
            if status.name == 'Under Review':
                try:
                    AllocationAdditionProcessingRunner(
                        self.request_obj)
                except AssertionError:
                    self.fail('An AssertionError should not have been raised.')
            else:
                try:
                    AllocationAdditionProcessingRunner(
                        self.request_obj)
                except AssertionError:
                    pass
                else:
                    self.fail('An AssertionError should have been raised.')

    def test_runner_creates_project_transaction(self):
        """Test that the runner creates a ProjectTransaction to record
        the change in service units."""
        request = self.request_obj
        project = self.project

        old_count = ProjectTransaction.objects.filter(project=project).count()
        pre_time = utc_now_offset_aware()

        runner = AllocationAdditionProcessingRunner(request)
        runner.run()

        post_time = utc_now_offset_aware()
        new_count = ProjectTransaction.objects.filter(project=project).count()
        self.assertEqual(old_count + 1, new_count)

        transaction = ProjectTransaction.objects.latest('date_time')
        self.assertTrue(pre_time <= transaction.date_time <= post_time)
        self.assertEqual(transaction.project, project)
        self.assertEqual(transaction.allocation, self.expected_post_sus)

    def test_runner_creates_project_user_transactions(self):
        """Test that the runner creates ProjectUserTransactions for all
        ProjectUsers to record the change in service units."""
        request = self.request_obj
        project = self.project

        queryset = ProjectUserTransaction.objects.filter(
            project_user__project=project)
        old_count = queryset.count()
        num_project_users = ProjectUser.objects.filter(project=project).count()
        pre_time = utc_now_offset_aware()

        runner = AllocationAdditionProcessingRunner(request)
        runner.run()

        post_time = utc_now_offset_aware()
        queryset = ProjectUserTransaction.objects.filter(
            project_user__project=project)
        new_count = queryset.count()
        self.assertEqual(old_count + num_project_users, new_count)

        transactions = queryset.filter(
            date_time__gt=pre_time, date_time__lt=post_time)
        for transaction in transactions:
            self.assertTrue(pre_time <= transaction.date_time <= post_time)
            self.assertEqual(transaction.project_user.project, project)
            self.assertEqual(transaction.allocation, self.expected_post_sus)

    def test_runner_sends_emails(self):
        """Test that the runner sends a notification email to the
        managers and PIs (who have notifications enabled) of the
        Project."""
        request = self.request_obj
        project = request.project

        # Create a PI who has disabled notifications and a Manager.
        self.other_pi = User.objects.create(
            email='other_pi@email.com',
            first_name='Other',
            last_name='PI',
            username='other_pi')
        ProjectUser.objects.create(
            project=self.project, user=self.other_pi,
            role=ProjectUserRoleChoice.objects.get(
                name='Principal Investigator'),
            status=ProjectUserStatusChoice.objects.get(name='Active'),
            enable_notifications=False)
        self.manager = User.objects.create(
            email='manager@email.com',
            first_name='Manager',
            last_name='User',
            username='manager')
        ProjectUser.objects.create(
            project=self.project, user=self.manager,
            role=ProjectUserRoleChoice.objects.get(
                name='Manager'),
            status=ProjectUserStatusChoice.objects.get(name='Active'))

        runner = AllocationAdditionProcessingRunner(request)
        runner.run()

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]

        self.assertIn('Purchase Request', email.subject)
        self.assertIn('Processed', email.subject)

        expected_body_snippets = [
            str(request.num_service_units),
            project.name,
            'processed',
            'current total allowance',
            str(self.expected_post_sus),
        ]
        for expected_body_snippet in expected_body_snippets:
            self.assertIn(expected_body_snippet, email.body)

        expected_from_email = settings.EMAIL_SENDER
        self.assertEqual(expected_from_email, email.from_email)

        expected_to = sorted([self.user.email, self.manager.email])
        self.assertEqual(expected_to, sorted(email.to))

    def test_runner_sets_status_and_completion_time(self):
        """Test that the runner sets the status of the request to
        'Complete' and its completion_time to the current time."""
        self.assertEqual(self.request_obj.status.name, 'Under Review')
        self.assertFalse(self.request_obj.completion_time)
        pre_time = utc_now_offset_aware()

        runner = AllocationAdditionProcessingRunner(self.request_obj)
        runner.run()

        post_time = utc_now_offset_aware()
        self.request_obj.refresh_from_db()
        completion_time = self.request_obj.completion_time
        self.assertEqual(self.request_obj.status.name, 'Complete')
        self.assertTrue(completion_time)
        self.assertTrue(pre_time <= completion_time <= post_time)

    def test_runner_updates_allocation_service_units_and_usage(self):
        """Test that the runner updates the AllocationAttribute with
        type 'Service Units' on the project's compute Allocation and its
        associated AllocationAttributeUsage."""
        request = self.request_obj
        project = request.project
        allocation = get_project_compute_allocation(project)

        self.assert_allocation_service_units_values(
            allocation, self.pre_allocation, self.pre_usage)

        runner = AllocationAdditionProcessingRunner(request)
        runner.run()

        allocation.refresh_from_db()
        self.assert_allocation_service_units_values(
            allocation, self.expected_post_sus, Decimal('0.00'))

    def test_runner_updates_allocation_user_service_units_and_usage(self):
        """Test that the runner updates the AllocationUserAttributes
        with 'Service Units' of the AllocationUsers of the project's
        compute Allocation and their associated
        AllocationUserAttributeUsages."""
        request = self.request_obj
        project = request.project
        allocation = get_project_compute_allocation(project)
        allocation_users = AllocationUser.objects.filter(allocation=allocation)
        self.assertEqual(allocation_users.count(), 2)

        for allocation_user in allocation_users:
            allocation, usage = self.values_by_user[allocation_user.user]
            self.assert_allocation_user_service_units_values(
                allocation_user, allocation, usage)

        runner = AllocationAdditionProcessingRunner(request)
        runner.run()

        allocation_users = AllocationUser.objects.filter(allocation=allocation)
        for allocation_user in allocation_users:
            allocation, usage = self.expected_post_sus, Decimal('0.00')
            self.assert_allocation_user_service_units_values(
                allocation_user, allocation, usage)
