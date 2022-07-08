from coldfront.api.statistics.utils import create_user_project_allocation
from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationAttribute
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AllocationAttributeUsage
from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.allocation.models import AllocationRenewalRequestStatusChoice
from coldfront.core.allocation.models import AllocationStatusChoice
from coldfront.core.allocation.models import AllocationUser
from coldfront.core.allocation.models import AllocationUserAttribute
from coldfront.core.allocation.models import AllocationUserAttributeUsage
from coldfront.core.allocation.models import AllocationUserStatusChoice
from coldfront.core.allocation.utils import get_project_compute_allocation
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.project.tests.test_utils.test_renewal_utils.utils import TestRunnerMixinBase
from coldfront.core.project.utils_.new_project_utils import SavioProjectProcessingRunner
from coldfront.core.project.utils_.renewal_utils import AllocationRenewalProcessingRunner
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period
from coldfront.core.project.utils_.renewal_utils import get_next_allowance_year_period
from coldfront.core.statistics.models import ProjectTransaction
from coldfront.core.statistics.models import ProjectUserTransaction
from coldfront.core.user.models import UserProfile
from coldfront.core.utils.common import display_time_zone_current_date
from coldfront.core.utils.common import utc_now_offset_aware
from datetime import date
from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.core import mail
from django.test import override_settings
from django.test import TestCase


class TestRunnerMixin(TestRunnerMixinBase):
    """A mixin for testing AllocationRenewalProcessingRunner."""

    def test_cluster_access_requests_created(self):
        """Test that the runner creates an AllocationUserAttribute with
        type 'Cluster Account Status' for the requester if one does not
        already exist."""
        request = self.request_obj
        project = request.post_project
        allocation = get_project_compute_allocation(project)

        # Delete all such attributes.
        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Cluster Account Status')
        AllocationUserAttribute.objects.filter(
            allocation_attribute_type=allocation_attribute_type).delete()

        num_service_units = Decimal('1000.00')
        runner = AllocationRenewalProcessingRunner(request, num_service_units)
        runner.run()

        # Only requesters should have an attribute, and it should be
        # 'Pending - Add'.
        allocation.refresh_from_db()
        queryset = allocation.allocationuser_set.all()
        for allocation_user in queryset:
            expected_num_attributes = int(
                allocation_user.user == self.requester)
            attributes = allocation_user.allocationuserattribute_set.filter(
                allocation_attribute_type=allocation_attribute_type)
            self.assertEqual(expected_num_attributes, attributes.count())
            if expected_num_attributes:
                self.assertEqual(attributes.first().value, 'Pending - Add')

    def test_cluster_access_requests_not_updated_if_active(self):
        """Test that the runner does not update existent, 'Active'.
        AllocationUserAttributes with type 'Cluster Account Status'."""
        request = self.request_obj
        project = request.post_project
        allocation = get_project_compute_allocation(project)

        # Only the requester should have one cluster access request. Set its
        # status to 'Active'.
        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Cluster Account Status')
        queryset = allocation.allocationuser_set.all()
        for allocation_user in queryset:
            expected_num_attributes = int(
                allocation_user.user == self.requester)
            attributes = allocation_user.allocationuserattribute_set.filter(
                allocation_attribute_type=allocation_attribute_type)
            self.assertEqual(expected_num_attributes, attributes.count())
            if expected_num_attributes:
                attributes.update(value='Active')

        num_service_units = Decimal('1000.00')
        runner = AllocationRenewalProcessingRunner(request, num_service_units)
        runner.run()

        # Only the requester should have one cluster access request, and it
        # should still be 'Active'.
        allocation.refresh_from_db()
        queryset = allocation.allocationuser_set.all()
        for allocation_user in queryset:
            expected_num_attributes = int(
                allocation_user.user == self.requester)
            attributes = allocation_user.allocationuserattribute_set.filter(
                allocation_attribute_type=allocation_attribute_type)
            self.assertEqual(expected_num_attributes, attributes.count())
            if expected_num_attributes:
                self.assertEqual(attributes.first().value, 'Active')

    def test_cluster_access_requests_updated_if_not_active(self):
        """Test that the runner updates existent, non-'Active'
        AllocationUserAttributes with type 'Cluster Account Status'."""
        request = self.request_obj
        project = request.post_project
        allocation = get_project_compute_allocation(project)

        # Only the requester should have one cluster access request. Set its
        # status to 'Denied'.
        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Cluster Account Status')
        queryset = allocation.allocationuser_set.all()
        for allocation_user in queryset:
            expected_num_attributes = int(
                allocation_user.user == self.requester)
            attributes = allocation_user.allocationuserattribute_set.filter(
                allocation_attribute_type=allocation_attribute_type)
            self.assertEqual(expected_num_attributes, attributes.count())
            if expected_num_attributes:
                attributes.update(value='Denied')

        num_service_units = Decimal('1000.00')
        runner = AllocationRenewalProcessingRunner(request, num_service_units)
        runner.run()

        # Only the requester should have one cluster access request, and it
        # should be 'Pending - Add'.
        allocation.refresh_from_db()
        queryset = allocation.allocationuser_set.all()
        for allocation_user in queryset:
            expected_num_attributes = int(
                allocation_user.user == self.requester)
            attributes = allocation_user.allocationuserattribute_set.filter(
                allocation_attribute_type=allocation_attribute_type)
            self.assertEqual(expected_num_attributes, attributes.count())
            if expected_num_attributes:
                self.assertEqual(attributes.first().value, 'Pending - Add')

    def test_num_service_units_validated(self):
        """Test that the provided number of service units must be valid,
        or an exception will be raised."""
        invalid_values = [
            '0.00',
            settings.ALLOCATION_MIN - Decimal('0.01'),
            settings.ALLOCATION_MAX + Decimal('0.01'),
            Decimal('1.00000000000'),
            Decimal('1.000'),
        ]
        exceptions = [
            TypeError(
                f'Number of service units {invalid_values[0]} is not a '
                f'Decimal.'),
            ValueError(
                f'Number of service units {invalid_values[1]} is not in the '
                f'acceptable range [{settings.ALLOCATION_MIN}, '
                f'{settings.ALLOCATION_MAX}].'),
            ValueError(
                f'Number of service units {invalid_values[2]} is not in the '
                f'acceptable range [{settings.ALLOCATION_MIN}, '
                f'{settings.ALLOCATION_MAX}].'),
            ValueError(
                f'Number of service units {invalid_values[3]} has greater '
                f'than {settings.DECIMAL_MAX_DIGITS} digits.'),
            ValueError(
                f'Number of service units {invalid_values[4]} has greater '
                f'than {settings.DECIMAL_MAX_PLACES} decimal places.'),
        ]
        for i in range(len(invalid_values)):
            try:
                AllocationRenewalProcessingRunner(
                    self.request_obj, invalid_values[i])
            except (TypeError, ValueError) as e:
                exception = exceptions[i]
                self.assertEqual(type(e), type(exception))
                self.assertEqual(str(e), str(exception))
            except Exception as e:
                self.fail(f'An unexpected Exception {e} was raised.')
            else:
                self.fail('A TypeError or ValueError should have been raised.')

    def test_project_users_different_requester_pi(self):
        """Test that, when the requester and PI are different users, the
        runner creates ProjectUser objects with the expected roles and
        statuses."""
        request = self.request_obj
        project = request.post_project
        requester = request.requester
        pi = request.pi
        # Delete the ProjectUsers on the Project in case they exist.
        ProjectUser.objects.filter(
            project=project, user__in=[requester, pi]).delete()
        self.assertNotEqual(request.requester, request.pi)

        num_service_units = Decimal('0.00')
        runner = AllocationRenewalProcessingRunner(request, num_service_units)
        runner.run()

        active_status = ProjectUserStatusChoice.objects.get(name='Active')
        roles = [(requester, 'Manager'), (pi, 'Principal Investigator')]
        for user, role_name in roles:
            try:
                project_user = ProjectUser.objects.get(
                    project=project, user=user)
            except ProjectUser.DoesNotExist:
                self.fail(
                    f'A ProjectUser should have been created for user {user}.')
            else:
                self.assertEqual(project_user.status, active_status)
                self.assertEqual(project_user.role.name, role_name)

    def test_project_users_different_requester_pi_both_already_pis(self):
        """Test that, when the requester and PI are different users, and
        both users are already PIs of the post_project, both are still
        PIs after the runner runs."""
        request = self.request_obj
        project = request.post_project
        requester = request.requester
        pi = request.pi
        # Set both to be 'Removed' PIs before the runner is run.
        removed_status = ProjectUserStatusChoice.objects.get(name='Removed')
        pi_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')
        for user in (requester, pi):
            try:
                project_user = ProjectUser.objects.get(
                    project=project, user=user)
            except ProjectUser.DoesNotExist:
                ProjectUser.objects.create(
                    project=project, user=user, role=pi_role,
                    status=removed_status)
            else:
                project_user.role = pi_role
                project_user.status = removed_status
                project_user.save()

        num_service_units = Decimal('0.00')
        runner = AllocationRenewalProcessingRunner(request, num_service_units)
        runner.run()

        active_status = ProjectUserStatusChoice.objects.get(name='Active')
        roles = [(requester, pi_role), (pi, pi_role)]
        for user, role in roles:
            try:
                project_user = ProjectUser.objects.get(
                    project=project, user=user)
            except ProjectUser.DoesNotExist:
                self.fail(
                    f'A ProjectUser should have been created for user {user}.')
            else:
                self.assertEqual(project_user.status, active_status)
                self.assertEqual(project_user.role, role)

    def test_project_users_same_requester_pi(self):
        """Test that, when the requester and PI are the same user, the
        runner creates a ProjectUser object, with the expected role and
        status."""
        request = self.request_obj
        project = request.post_project
        requester = request.requester
        pi = request.pi
        # Delete the ProjectUsers on the Project in case they exist.
        ProjectUser.objects.filter(
            project=project, user__in=[requester, pi]).delete()
        # Update the requester to be the PI as well.
        request.requester = pi
        request.save()
        self.assertEqual(request.requester, request.pi)

        num_service_units = Decimal('0.00')
        runner = AllocationRenewalProcessingRunner(request, num_service_units)
        runner.run()

        project_users = ProjectUser.objects.filter(project=project, user=pi)
        active_status = ProjectUserStatusChoice.objects.get(name='Active')
        project_user = project_users.first()
        self.assertEqual(project_user.status, active_status)
        self.assertEqual(project_user.role.name, 'Principal Investigator')

    def test_request_allocation_period_not_ended_enforced(self):
        """Test that the provided AllocationRenewalRequest's
        AllocationPeriod must not have ended, or an exception will be
        raised."""
        allocation_period = AllocationPeriod.objects.filter(
            name__startswith='Allowance Year',
            end_date__lt=display_time_zone_current_date()).first()
        self.request_obj.allocation_period = allocation_period
        self.request_obj.save()
        num_service_units = Decimal('0.00')
        try:
            AllocationRenewalProcessingRunner(
                self.request_obj, num_service_units)
        except AssertionError as e:
            message = (
                f'AllocationPeriod already ended on '
                f'{allocation_period.end_date}.')
            self.assertEqual(str(e), message)

    def test_request_allocation_period_started_enforced(self):
        """Test that the provided AllocationRenewalRequest's
        AllocationPeriod must have started, or an exception will be
        raised."""
        allocation_period = get_next_allowance_year_period()
        self.request_obj.allocation_period = allocation_period
        self.request_obj.save()
        num_service_units = Decimal('0.00')
        try:
            AllocationRenewalProcessingRunner(
                self.request_obj, num_service_units)
        except AssertionError as e:
            message = (
                f'AllocationPeriod does not start until '
                f'{allocation_period.start_date}.')
            self.assertEqual(str(e), message)

    def test_request_initial_approved_status_enforced(self):
        """Test that the provided AllocationRenewalRequest must be in
        the 'Approved' state, or an exception will be raised."""
        statuses = AllocationRenewalRequestStatusChoice.objects.all()
        self.assertEqual(statuses.count(), 4)
        num_service_units = Decimal('0.00')
        for status in statuses:
            self.request_obj.status = status
            self.request_obj.save()
            if status.name == 'Approved':
                AllocationRenewalProcessingRunner(
                    self.request_obj, num_service_units)
            else:
                try:
                    AllocationRenewalProcessingRunner(
                        self.request_obj, num_service_units)
                except AssertionError as e:
                    message = 'The request must have status \'Approved\'.'
                    self.assertEqual(str(e), message)
                    continue
                else:
                    self.fail('An AssertionError should have been raised.')

    def test_runner_activates_allocation(self):
        """Test that runner sets the post_project's compute Allocation's
        status to 'Active'."""
        request = self.request_obj
        project = request.post_project
        allocation = get_project_compute_allocation(project)
        # Set its status to 'New' before the runner is run.
        allocation.status = AllocationStatusChoice.objects.get(name='New')
        allocation.save()

        num_service_units = Decimal('0.00')
        runner = AllocationRenewalProcessingRunner(request, num_service_units)
        runner.run()

        allocation.refresh_from_db()
        expected_allocation_status = AllocationStatusChoice.objects.get(
            name='Active')
        self.assertEqual(expected_allocation_status, allocation.status)

    def test_runner_activates_project(self):
        """Test that the runner sets the post_project's status to
        'Active'."""
        project = self.request_obj.post_project
        # Set its status to 'New' before the runner is run.
        project.status = ProjectStatusChoice.objects.get(name='New')
        project.save()

        num_service_units = Decimal('1000.00')
        runner = AllocationRenewalProcessingRunner(
            self.request_obj, num_service_units)
        runner.run()

        project.refresh_from_db()
        self.assertEqual(project.status.name, 'Active')

    def test_runner_creates_and_updates_allocation_users(self):
        """Test that the runner creates new AllocationUsers and updates
        existing AllocationUsers on the post_project's compute
        Allocation."""
        request = self.request_obj
        project = request.post_project
        allocation = get_project_compute_allocation(project)

        # Initially, there should be an AllocationUser for the requester, and
        # there may be one for the PI.
        queryset = allocation.allocationuser_set.all()
        try:
            a = queryset.get(user=request.requester)
        except AllocationUser.DoesNotExist:
            self.fail('The requester should have an AllocationUser.')
        try:
            b = queryset.get(user=request.pi)
        except AllocationUser.DoesNotExist:
            b = None
        # Delete the requester's AllocationUser to test that it gets created.
        a.delete()
        # Change the PI's AllocationUser's status if it exists to test that it
        # gets updated.
        if b:
            b.status = AllocationUserStatusChoice.objects.get(name='Removed')
            b.save()

        num_service_units = Decimal('1000.00')
        runner = AllocationRenewalProcessingRunner(request, num_service_units)
        runner.run()

        # Both should exist and both should have status 'Active'.
        allocation.refresh_from_db()
        queryset = allocation.allocationuser_set.all()
        try:
            a = queryset.get(user=request.requester)
        except AllocationUser.DoesNotExist:
            self.fail('The requester should have an AllocationUser.')
        try:
            b = queryset.get(user=request.pi)
        except AllocationUser.DoesNotExist:
            self.fail('The PI should have an AllocationUser.')
        self.assertEqual(a.status.name, 'Active')
        self.assertEqual(b.status.name, 'Active')

    def test_runner_creates_project_transaction(self):
        """Test that the runner creates a ProjectTransaction to record
        the change in service units."""
        request = self.request_obj
        project = request.post_project

        old_count = ProjectTransaction.objects.filter(project=project).count()
        pre_time = utc_now_offset_aware()

        num_service_units = Decimal('1000.00')
        runner = AllocationRenewalProcessingRunner(request, num_service_units)
        runner.run()

        post_time = utc_now_offset_aware()
        new_count = ProjectTransaction.objects.filter(project=project).count()
        self.assertEqual(old_count + 1, new_count)

        transaction = ProjectTransaction.objects.latest('date_time')
        new_allocation_value = \
            self.project_service_units[project] + num_service_units
        self.assertTrue(pre_time <= transaction.date_time <= post_time)
        self.assertEqual(transaction.project, project)
        self.assertEqual(transaction.allocation, new_allocation_value)

    def test_runner_creates_project_user_transactions(self):
        """Test that the runner creates ProjectUserTransactions for all
        ProjectUsers who were already on the Project to record the
        change in service units."""
        request = self.request_obj
        project = request.post_project

        # Create AllocationUsers and set 'Service Units'.
        project_users = project.projectuser_set.all()
        self.assertTrue(project_users)
        allocation = get_project_compute_allocation(project)
        AllocationUser.objects.filter(allocation=allocation).delete()
        for project_user in project_users:
            create_user_project_allocation(
                project_user.user, project,
                self.project_service_units[project])

        queryset = ProjectUserTransaction.objects.filter(
            project_user__project=project)
        old_count = queryset.count()
        num_project_users = project_users.count()
        pre_time = utc_now_offset_aware()

        num_service_units = Decimal('1000.00')
        runner = AllocationRenewalProcessingRunner(request, num_service_units)
        runner.run()

        post_time = utc_now_offset_aware()
        queryset = ProjectUserTransaction.objects.filter(
            project_user__project=project)
        new_count = queryset.count()
        self.assertEqual(old_count + num_project_users, new_count)

        transactions = queryset.filter(
            date_time__gt=pre_time, date_time__lt=post_time)
        new_allocation_value = \
            self.project_service_units[project] + num_service_units
        for transaction in transactions:
            self.assertTrue(pre_time <= transaction.date_time <= post_time)
            self.assertEqual(transaction.project_user.project, project)
            self.assertEqual(transaction.allocation, new_allocation_value)

    def test_runner_not_resets_service_units_usages(self):
        """Test that the runner does not set AllocationAttributeUsage
        and AllocationUserAttributeUsage values for the 'Service Units'
        attribute to zero."""
        request = self.request_obj
        project = request.post_project
        allocation = get_project_compute_allocation(project)
        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Service Units')

        # Set the Project's overall usage to a non-zero value.
        value = Decimal('100.00')
        project_usages = AllocationAttributeUsage.objects.filter(
            allocation_attribute__allocation=allocation)
        self.assertEqual(project_usages.count(), 1)
        project_usage = project_usages.first()
        self.assertEqual(
            allocation_attribute_type,
            project_usage.allocation_attribute.allocation_attribute_type)
        project_usage.value = value
        project_usage.save()

        # Create AllocationUsers and set 'Service Units'.
        project_users = project.projectuser_set.all()
        self.assertTrue(project_users)
        AllocationUser.objects.filter(allocation=allocation).delete()
        for project_user in project_users:
            create_user_project_allocation(
                project_user.user, project,
                self.project_service_units[project])

        # Set each ProjectUser's usage to a non-zero value.
        project_user_usages = AllocationUserAttributeUsage.objects.filter(
            allocation_user_attribute__allocation=allocation)
        self.assertGreater(project_user_usages.count(), 0)
        project_user_usages_cache = []
        for usage in project_user_usages:
            self.assertEqual(
                allocation_attribute_type,
                usage.allocation_user_attribute.allocation_attribute_type)
            usage.value = value
            usage.save()
            project_user_usages_cache.append(usage)

        num_service_units = Decimal('1000.00')
        runner = AllocationRenewalProcessingRunner(request, num_service_units)
        runner.run()

        # The values should not have changed.
        project_usage.refresh_from_db()
        self.assertEqual(value, project_usage.value)
        for usage in project_user_usages_cache:
            usage.refresh_from_db()
            self.assertEqual(value, usage.value)

    @override_settings(
        REQUEST_APPROVAL_CC_LIST=['admin0@email.com', 'admin1@email.com'])
    def test_runner_sends_emails(self):
        """Test that the runner sends a notification email to the
        requester and the PI, CC'ing a designated list of admins."""
        request = self.request_obj
        project = request.post_project
        requester = request.requester
        pi = request.pi

        num_service_units = Decimal('1000.00')
        runner = AllocationRenewalProcessingRunner(request, num_service_units)
        runner.run()

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]

        expected_subject = (
            f'{settings.EMAIL_SUBJECT_PREFIX} {str(request)} Processed')
        self.assertEqual(expected_subject, email.subject)

        expected_body_snippets = [
            (f'{num_service_units} service units have been added to the '
             f'project {project.name}.'),
            f'/project/{project.pk}/',
        ]
        for expected_body_snippet in expected_body_snippets:
            self.assertIn(expected_body_snippet, email.body)

        expected_from_email = settings.EMAIL_SENDER
        self.assertEqual(expected_from_email, email.from_email)

        expected_to = sorted([requester.email, pi.email])
        self.assertEqual(expected_to, sorted(email.to))

        expected_cc = ['admin0@email.com', 'admin1@email.com']
        self.assertEqual(expected_cc, sorted(email.cc))

    def test_runner_sets_allocation_dates_if_allocation_inactive(self):
        """Test that te runner sets the post_project's compute
        Allocation's start_date and end_date if the Project's status is
         not 'Active'."""
        request = self.request_obj
        project = request.post_project
        allocation = get_project_compute_allocation(project)

        # Deactivate the Project and nullify the dates.
        project.status = ProjectStatusChoice.objects.get(name='Inactive')
        project.save()
        allocation.start_date = None
        allocation.end_date = None
        allocation.save()

        num_service_units = Decimal('1000.00')
        runner = AllocationRenewalProcessingRunner(request, num_service_units)
        runner.run()

        # Both dates should have been updated.
        allocation.refresh_from_db()
        self.assertIsNotNone(allocation.start_date)
        self.assertIsNotNone(allocation.end_date)

    def test_runner_sets_allocation_dates_if_not_set(self):
        """Test that the runner sets the post_project's compute
        Allocation's start_date and/or end_date if they are not set."""
        request = self.request_obj
        project = request.post_project
        allocation = get_project_compute_allocation(project)

        # Set the end_date, but not the start_date.
        today = display_time_zone_current_date()
        allocation.start_date = None
        end_date = today + timedelta(days=30)
        allocation.end_date = end_date
        allocation.save()

        num_service_units = Decimal('1000.00')
        runner = AllocationRenewalProcessingRunner(request, num_service_units)
        runner.run()

        # The start_date should have been updated, but not the end_date.
        allocation.refresh_from_db()
        self.assertEqual(today, allocation.start_date)
        self.assertEqual(end_date, allocation.end_date)

    def test_runner_sets_is_pi_field_of_pi_user_profile(self):
        """Test that the User designated as the PI on the request has
        the is_pi field set to True in its UserProfile."""
        request = self.request_obj
        pi_user_profile = UserProfile.objects.get(user=request.pi)
        pi_user_profile.is_pi = False
        pi_user_profile.save()

        num_service_units = Decimal('0.00')
        runner = AllocationRenewalProcessingRunner(request, num_service_units)
        runner.run()

        pi_user_profile.refresh_from_db()
        self.assertTrue(pi_user_profile.is_pi)

    def test_runner_sets_request_num_service_units(self):
        """Test that the runner sets the provided number of service
        units in the request."""
        request = self.request_obj
        self.assertEqual(request.num_service_units, Decimal('0.00'))

        num_service_units = Decimal('1000.00')
        runner = AllocationRenewalProcessingRunner(request, num_service_units)
        runner.run()

        request.refresh_from_db()
        self.assertEqual(request.num_service_units, num_service_units)

    def test_runner_sets_status_and_completion_time(self):
        """Test that the runner sets the status of the request to
        'Complete' and its completion_time to the current time."""
        self.assertEqual(self.request_obj.status.name, 'Approved')
        self.assertFalse(self.request_obj.completion_time)
        pre_time = utc_now_offset_aware()

        num_service_units = Decimal('0.00')
        runner = AllocationRenewalProcessingRunner(
            self.request_obj, num_service_units)
        runner.run()

        post_time = utc_now_offset_aware()
        self.request_obj.refresh_from_db()
        completion_time = self.request_obj.completion_time
        self.assertEqual(self.request_obj.status.name, 'Complete')
        self.assertTrue(completion_time)
        self.assertTrue(pre_time <= completion_time <= post_time)

    def test_runner_updates_allocation_failure_if_not_exists(self):
        """Test that an exception is raised when attempting to update
        the nonexistent compute Allocation of the post_project."""
        request = self.request_obj
        project = request.post_project
        try:
            allocation = get_project_compute_allocation(project)
        except Allocation.DoesNotExist:
            self.fail(f'Project {project.name} has no compute Allocation.')
        allocation.delete()
        try:
            get_project_compute_allocation(project)
        except Allocation.DoesNotExist:
            pass
        else:
            self.fail(
                f'Project {project.name}\'s compute Allocation should have '
                f'been deleted.')

        num_service_units = Decimal('0.00')
        runner = AllocationRenewalProcessingRunner(request, num_service_units)
        try:
            runner.run()
        except Allocation.DoesNotExist:
            pass
        else:
            self.fail(
                'The runner should have failed due to a nonexistent compute '
                'Allocation.')

    def test_runner_updates_allocation_service_units(self):
        """Test that the runner updates the AllocationAttribute with
        type 'Service Units' on the post_project's compute
        Allocation."""
        request = self.request_obj
        project = request.post_project
        allocation = get_project_compute_allocation(project)

        expected_previous_value = self.project_service_units[project]
        self.assert_allocation_service_units_value(
            allocation, expected_previous_value)

        num_service_units = Decimal('1000.00')
        runner = AllocationRenewalProcessingRunner(request, num_service_units)
        runner.run()

        allocation.refresh_from_db()
        expected_current_value = expected_previous_value + num_service_units
        self.assert_allocation_service_units_value(
            allocation, expected_current_value)

    def test_runner_updates_allocation_user_service_units(self):
        """Test that the runner updates the AllocationUserAttributes
        with type 'Service Units' on the AllocationUsers of the
        post_project's compute Allocation."""
        request = self.request_obj
        project = request.post_project
        allocation = get_project_compute_allocation(project)

        # Create AllocationUsers and set 'Service Units'.
        project_users = project.projectuser_set.all()
        self.assertTrue(project_users)
        attributes_cache = []
        AllocationUser.objects.filter(allocation=allocation).delete()
        value = self.project_service_units[project]
        for project_user in project_users:
            allocation_objects = create_user_project_allocation(
                project_user.user, project, value)
            attributes_cache.append(
                allocation_objects.allocation_user_attribute)

        num_service_units = Decimal('1000.00')
        runner = AllocationRenewalProcessingRunner(request, num_service_units)
        runner.run()

        for attribute in attributes_cache:
            attribute.refresh_from_db()
            new_allocation_value = str(value + num_service_units)
            self.assertEqual(attribute.value, new_allocation_value)


class TestFutureRequestsUpdateMixin(object):
    """A mixin for testing that future AllocationRenewalRequests may be
    updated as a result of processing."""

    def create_different_project_and_request(self, project_name):
        """Create an AllocationRenewalRequest that shares a pre_project
        with the request to-be-processed, but has a different
        post_project, with the given name."""
        request = self.request_obj

        self.different_project = Project.objects.create(
            name=project_name,
            title=project_name,
            status=ProjectStatusChoice.objects.get(name='Active'))

        allocation_period = get_next_allowance_year_period()
        approved_status = AllocationRenewalRequestStatusChoice.objects.get(
            name='Approved')

        return AllocationRenewalRequest.objects.create(
            requester=request.requester,
            pi=request.pi,
            allocation_period=allocation_period,
            status=approved_status,
            pre_project=request.pre_project,
            post_project=self.different_project,
            num_service_units=Decimal('0.00'),
            request_time=utc_now_offset_aware())

    def assert_update_message_logged(self, future_request, log_messages,
                                     expected=True):
        """Given a list of strings representing messages written to the
        log during processing, assert that a message about the future
        request being updated is (not) included.."""
        expected_log_substring = (
            f'Updated AllocationRenewalRequest {future_request.pk}\'s '
            f'pre_project from {self.request_obj.pre_project.pk} to '
            f'{self.request_obj.post_project.pk}')
        message_found = False
        for log_message in log_messages:
            if expected_log_substring in log_message:
                message_found = True
                break
        self.assertEqual(expected, message_found)

    def test_not_updates_request_not_matching_all_conditions(self):
        """Test that AllocationRenewalRequests that do not meet all
        conditions for being updated are not updated."""
        request = self.request_obj

        future_requests = []
        for i in range(4):
            future_requests.append(
                self.create_different_project_and_request(f'fc_different_{i}'))

        # The first request has a 'Complete' or 'Denied' status.
        future_requests[0].status = \
            AllocationRenewalRequestStatusChoice.objects.get(name='Complete')
        future_requests[0].save()
        # The second request is for an AllocationPeriod that has already
        # started.
        future_requests[1].allocation_period = \
            get_current_allowance_year_period()
        future_requests[1].save()
        # The third request has a different allocation type.
        future_requests[2].pre_project.name = (
            f'ic_{future_requests[2].pre_project.name}')
        future_requests[2].pre_project.save()
        # The fourth request has a different PI.
        future_requests[3].pi = future_requests[3].requester
        future_requests[3].save()

        relevant_pooling_cases = [
            AllocationRenewalRequest.UNPOOLED_TO_POOLED,
            AllocationRenewalRequest.POOLED_TO_POOLED_DIFFERENT,
            AllocationRenewalRequest.POOLED_TO_UNPOOLED_OLD,
            AllocationRenewalRequest.POOLED_TO_UNPOOLED_NEW,
        ]
        project_changed = (
            request.get_pooling_preference_case() in relevant_pooling_cases)

        log_args = ('coldfront.core.project.utils_.renewal_utils', 'INFO')
        tmp_status = request.status
        tmp_pre_project = request.pre_project
        tmp_post_project = request.post_project
        already_pi_of_post = request.pi in tmp_post_project.pis()
        project_pi_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')
        project_user_role = ProjectUserRoleChoice.objects.get(name='User')
        for future_request in future_requests:
            num_service_units = Decimal('0.00')
            runner = AllocationRenewalProcessingRunner(
                request, num_service_units)
            with self.assertLogs(*log_args) as cm:
                runner.run()
            self.assert_update_message_logged(
                future_request, cm.output, expected=False)
            # Reset the request fields and other changed state.
            request.status = tmp_status
            request.pre_project = tmp_pre_project
            request.post_project = tmp_post_project
            ProjectUser.objects.filter(
                project=request.pre_project, user=request.pi).update(
                    role=project_pi_role)
            if not already_pi_of_post:
                ProjectUser.objects.filter(
                    project=request.post_project, user=request.pi).update(
                        role=project_user_role)
            request.save()

        # In cases where the pre_project of the future request was already
        # equal to the post_project of the processed request, the two are
        # trivially equal. In other cases, the future request's pre_project
        # should not have been updated.
        future_request.refresh_from_db()
        if project_changed:
            self.assertNotEqual(
                future_request.pre_project, request.post_project)
        else:
            self.assertEqual(future_request.pre_project, request.post_project)

    def test_updates_request_matching_all_conditions(self):
        """Test that an AllocationRenewalRequest that meets all
        conditions for being updated is updated."""
        request = self.request_obj
        # Update the pre_project to have a proper prefix.
        request.pre_project.name = f'fc_{request.pre_project.name}'
        request.pre_project.save()

        future_request = self.create_different_project_and_request(
            'fc_different')

        relevant_pooling_cases = [
            AllocationRenewalRequest.UNPOOLED_TO_POOLED,
            AllocationRenewalRequest.POOLED_TO_POOLED_DIFFERENT,
            AllocationRenewalRequest.POOLED_TO_UNPOOLED_OLD,
            AllocationRenewalRequest.POOLED_TO_UNPOOLED_NEW,
        ]
        project_changed = (
            request.get_pooling_preference_case() in relevant_pooling_cases)

        # The future request has the 'Approved' status; more specifically, it
        # does not have the 'Complete' or 'Denied' statuses.
        self.assertEqual(future_request.status.name, 'Approved')
        # The future request's AllocationPeriod has not started yet.
        current_date = display_time_zone_current_date()
        self.assertGreater(
            future_request.allocation_period.start_date, current_date)
        # The future request has the same allocation type as this one.
        self.assertEqual(
            future_request.pre_project.name[3:], request.pre_project.name[3:])
        # The future request has the same PI as this one.
        self.assertEqual(future_request.pi, request.pi)
        # The future request has a different pre_project than this one's
        # post_project, if this request's project changed.
        if project_changed:
            self.assertNotEqual(
                future_request.pre_project, request.post_project)
        else:
            self.assertEqual(future_request.pre_project, request.post_project)

        num_service_units = Decimal('0.00')
        runner = AllocationRenewalProcessingRunner(request, num_service_units)
        with self.assertLogs(
                'coldfront.core.project.utils_.renewal_utils', 'INFO') as cm:
            runner.run()
        self.assert_update_message_logged(
            future_request, cm.output, expected=project_changed)

        # In all cases, the future request's pre_project should match this
        # one's post_project.
        future_request.refresh_from_db()
        self.assertEqual(future_request.pre_project, request.post_project)


class TestPIDemotionMixin(object):
    """A mixin for testing PI demotion to the 'User' role."""

    def test_pre_project_pi_demoted_if_pooled(self):
        """Test that the PI is demoted to the 'User' role on the
        pre_project if it has at least one other PI."""
        request = self.request_obj
        pi = request.pi
        project = request.pre_project

        pi_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')
        user_role = ProjectUserRoleChoice.objects.get(name='User')

        num_pis = project.pis().count()
        self.assertGreater(num_pis, 1)
        try:
            pi_project_user = project.projectuser_set.get(user=pi)
        except ProjectUser.DoesNotExist:
            self.fail('The PI is not a member of the pre_project.')

        self.assertEqual(pi_role, pi_project_user.role)

        num_service_units = Decimal('1000.00')
        runner = AllocationRenewalProcessingRunner(request, num_service_units)
        runner.run()

        self.assertEqual(project.pis().count(), num_pis - 1)
        pi_project_user.refresh_from_db()
        self.assertEqual(user_role, pi_project_user.role)


class TestUnpooledToUnpooled(TestFutureRequestsUpdateMixin, TestRunnerMixin,
                             TestCase):
    """A class for testing the AllocationRenewalProcessingRunner in the
    'unpooled_to_unpooled' case."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.request_obj = self.create_request(
            status=AllocationRenewalRequestStatusChoice.objects.get(
                name='Approved'),
            pi=self.pi0,
            pre_project=self.unpooled_project0,
            post_project=self.unpooled_project0)

    def test_pooling_preference_case(self):
        """Test that the pooling preference case for the class' renewal
        request is 'unpooled_to_unpooled'."""
        self.assert_pooling_preference_case(
            AllocationRenewalRequest.UNPOOLED_TO_UNPOOLED)


class TestUnpooledToPooled(TestFutureRequestsUpdateMixin, TestRunnerMixin,
                           TestCase):
    """A class for testing the AllocationRenewalProcessingRunner in the
    'unpooled_to_pooled' case."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.request_obj = self.create_request(
            status=AllocationRenewalRequestStatusChoice.objects.get(
                name='Approved'),
            pi=self.pi0,
            pre_project=self.unpooled_project0,
            post_project=self.pooled_project1)

    def test_pooling_preference_case(self):
        """Test that the pooling preference case for the class' renewal
        request is 'unpooled_to_pooled'."""
        self.assert_pooling_preference_case(
            AllocationRenewalRequest.UNPOOLED_TO_POOLED)


class TestPooledToPooledSame(TestFutureRequestsUpdateMixin, TestRunnerMixin,
                             TestCase):
    """A class for testing the AllocationRenewalProcessingRunner in the
    'pooled_to_pooled_same' case."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.request_obj = self.create_request(
            status=AllocationRenewalRequestStatusChoice.objects.get(
                name='Approved'),
            pi=self.pi0,
            pre_project=self.pooled_project0,
            post_project=self.pooled_project0)

    def test_pooling_preference_case(self):
        """Test that the pooling preference case for the class' renewal
        request is 'pooled_to_pooled_same'."""
        self.assert_pooling_preference_case(
            AllocationRenewalRequest.POOLED_TO_POOLED_SAME)


class TestPooledToPooledDifferent(TestFutureRequestsUpdateMixin,
                                  TestPIDemotionMixin, TestRunnerMixin,
                                  TestCase):
    """A class for testing the AllocationRenewalProcessingRunner in the
    'pooled_to_pooled_different' case."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.request_obj = self.create_request(
            status=AllocationRenewalRequestStatusChoice.objects.get(
                name='Approved'),
            pi=self.pi0,
            pre_project=self.pooled_project0,
            post_project=self.pooled_project1)

    def test_pooling_preference_case(self):
        """Test that the pooling preference case for the class' renewal
        request is 'pooled_to_pooled_different'."""
        self.assert_pooling_preference_case(
            AllocationRenewalRequest.POOLED_TO_POOLED_DIFFERENT)


class TestPooledToUnpooledOld(TestFutureRequestsUpdateMixin,
                              TestPIDemotionMixin, TestRunnerMixin, TestCase):
    """A class for testing the AllocationRenewalProcessingRunner in the
    'pooled_to_unpooled_old' case."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.request_obj = self.create_request(
            status=AllocationRenewalRequestStatusChoice.objects.get(
                name='Approved'),
            pi=self.pi0,
            pre_project=self.pooled_project0,
            post_project=self.unpooled_project0)

    def test_pooling_preference_case(self):
        """Test that the pooling preference case for the class' renewal
        request is 'pooled_to_unpooled_old'."""
        self.assert_pooling_preference_case(
            AllocationRenewalRequest.POOLED_TO_UNPOOLED_OLD)


class TestPooledToUnpooledNew(TestFutureRequestsUpdateMixin,
                              TestPIDemotionMixin, TestRunnerMixin, TestCase):
    """A class for testing the AllocationRenewalProcessingRunner in the
    'pooled_to_unpooled_new' case."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        new_project_request = \
            self.simulate_new_project_allocation_request_processing()
        self.request_obj = self.create_request(
            status=AllocationRenewalRequestStatusChoice.objects.get(
                name='Approved'),
            pi=self.pi0,
            pre_project=self.pooled_project0,
            post_project=new_project_request.project,
            new_project_request=new_project_request)

    def simulate_new_project_allocation_request_processing(self):
        """Create a new Project and simulate its processing. Return the
        created SavioProjectAllocationRequest."""
        new_project_request = self.create_under_review_new_project_request()
        new_project = new_project_request.project

        # Process the request.
        num_service_units = Decimal('1000.00')
        runner = SavioProjectProcessingRunner(
            new_project_request, num_service_units)
        runner.run()
        # Clear the mail outbox.
        mail.outbox = []

        # Store the number of service units set.
        self.project_service_units[new_project] = num_service_units

        new_project_request.refresh_from_db()
        expected_status_name = 'Approved - Complete'
        self.assertEqual(expected_status_name, new_project_request.status.name)

        return new_project_request

    def test_pooling_preference_case(self):
        """Test that the pooling preference case for the class' renewal
        request is 'pooled_to_unpooled_new'."""
        self.assert_pooling_preference_case(
            AllocationRenewalRequest.POOLED_TO_UNPOOLED_NEW)
