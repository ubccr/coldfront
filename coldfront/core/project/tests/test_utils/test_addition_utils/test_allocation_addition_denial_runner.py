from coldfront.api.statistics.utils import create_project_allocation
from coldfront.api.statistics.utils import create_user_project_allocation
from coldfront.api.statistics.utils import set_project_usage_value
from coldfront.api.statistics.utils import set_project_user_usage_value
from coldfront.core.allocation.models import AllocationAdditionRequest
from coldfront.core.allocation.models import AllocationAdditionRequestStatusChoice
from coldfront.core.allocation.models import AllocationUser
from coldfront.core.allocation.utils import get_project_compute_allocation
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.tests.test_utils.test_addition_utils.test_runner_mixin import TestRunnerMixin
from coldfront.core.project.utils_.addition_utils import AllocationAdditionDenialRunner
from coldfront.core.statistics.models import ProjectTransaction
from coldfront.core.statistics.models import ProjectUserTransaction
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import TestBase

from decimal import Decimal
from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail


class TestAllocationAdditionDenialRunner(TestRunnerMixin, TestBase):
    """A class for testing AllocationAdditionDenialRunner."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)

        self.project = self.create_active_project_with_pi(
            'ac_project', self.user)

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

        self.values_by_user = {
            self.user: user_values,
        }

        # The request will add 300 SUs.
        self.sus_addition = Decimal('300.00')
        self.request_obj = \
            AllocationAdditionRequest.objects.create(
                requester=self.user,
                project=self.project,
                status=AllocationAdditionRequestStatusChoice.objects.get(
                    name='Under Review'),
                num_service_units=self.sus_addition)

    def test_request_status_validated(self):
        """Test that the runner raises an error if the request does not
        have the 'Under Review' status."""
        for status in AllocationAdditionRequestStatusChoice.objects.all():
            self.request_obj.status = status
            self.request_obj.save()
            if status.name == 'Under Review':
                try:
                    AllocationAdditionDenialRunner(self.request_obj)
                except AssertionError:
                    self.fail('An AssertionError should not have been raised.')
            else:
                try:
                    AllocationAdditionDenialRunner(self.request_obj)
                except AssertionError:
                    pass
                else:
                    self.fail('An AssertionError should have been raised.')

    def test_runner_not_creates_transactions(self):
        """Test that the runner does not create ProjectTransactions or
        ProjectUserTransactions."""
        request = self.request_obj
        project = self.project

        old_project_transaction_count = ProjectTransaction.objects.filter(
            project=project).count()
        old_project_user_transaction_count = \
            ProjectUserTransaction.objects.filter(
                project_user__project=self.project).count()

        runner = AllocationAdditionDenialRunner(request)
        runner.run()

        new_project_transaction_count = ProjectTransaction.objects.filter(
            project=project).count()
        new_project_user_transaction_count = \
            ProjectUserTransaction.objects.filter(
                project_user__project=self.project).count()

        self.assertEqual(
            old_project_transaction_count, new_project_transaction_count)
        self.assertEqual(
            old_project_user_transaction_count,
            new_project_user_transaction_count)

    def test_runner_not_updates_allocation_service_units_or_usage(self):
        """Test that the runner does not update AllocationAttributes,
        AllocationAttributeUsages, AllocationUserAttributes, or
        AllocationUserAttributeUsages."""
        request = self.request_obj
        project = request.project
        allocation = get_project_compute_allocation(project)
        allocation_users = AllocationUser.objects.filter(allocation=allocation)
        self.assertEqual(allocation_users.count(), 1)

        self.assert_allocation_service_units_values(
            allocation, self.pre_allocation, self.pre_usage)

        for allocation_user in allocation_users:
            _allocation, usage = self.values_by_user[allocation_user.user]
            self.assert_allocation_user_service_units_values(
                allocation_user, _allocation, usage)

        runner = AllocationAdditionDenialRunner(self.request_obj)
        runner.run()

        self.assert_allocation_service_units_values(
            allocation, self.pre_allocation, self.pre_usage)

        for allocation_user in allocation_users:
            _allocation, usage = self.values_by_user[allocation_user.user]
            self.assert_allocation_user_service_units_values(
                allocation_user, _allocation, usage)

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

        self.request_obj.state['other'] = {
            'justification': 'Test denial reason.',
            'timestamp': utc_now_offset_aware().isoformat(),
        }

        runner = AllocationAdditionDenialRunner(self.request_obj)
        runner.run()

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]

        self.assertIn('Purchase Request', email.subject)
        self.assertIn('Denied', email.subject)

        expected_body_snippets = [
            str(request.num_service_units),
            project.name,
            'denied',
            'following reason',
            'Other',
            f'{self.request_obj.state["other"]["justification"]}',
        ]
        for expected_body_snippet in expected_body_snippets:
            self.assertIn(expected_body_snippet, email.body)

        expected_from_email = settings.EMAIL_SENDER
        self.assertEqual(expected_from_email, email.from_email)

        expected_to = sorted([self.user.email, self.manager.email])
        self.assertEqual(expected_to, sorted(email.to))

    def test_runner_sets_status(self):
        """Test that the sets the status of the request to 'Denied'."""
        self.assertEqual(self.request_obj.status.name, 'Under Review')

        runner = AllocationAdditionDenialRunner(self.request_obj)
        runner.run()

        self.request_obj.refresh_from_db()
        self.assertEqual(self.request_obj.status.name, 'Denied')
