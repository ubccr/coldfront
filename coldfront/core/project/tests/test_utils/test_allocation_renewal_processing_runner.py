from coldfront.api.statistics.utils import create_project_allocation
from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.allocation.models import AllocationRenewalRequestStatusChoice
from coldfront.core.allocation.utils import get_project_compute_allocation
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.utils_.renewal_utils import AllocationRenewalProcessingRunner
from coldfront.core.user.models import UserProfile
from coldfront.core.utils.common import utc_now_offset_aware
from decimal import Decimal
from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.core.management import call_command
from django.test import override_settings
from django.test import TestCase
from io import StringIO
import os
import sys


class TestRunnerMixin(object):
    """A base mixin for testing AllocationRenewalProcessingRunner."""

    def setUp(self):
        """Set up test data."""
        out, err = StringIO(), StringIO()
        commands = [
            'add_resource_defaults',
            'add_allocation_defaults',
            'add_brc_accounting_defaults',
            'create_allocation_periods',
            'import_field_of_science_data',
            'add_default_project_choices',
        ]
        sys.stdout = open(os.devnull, 'w')
        for command in commands:
            call_command(command, stdout=out, stderr=err)
        sys.stdout = sys.__stdout__

        self.allocation_period = AllocationPeriod.objects.get(name='AY21-22')

        # TODO
        requester = User.objects.create(
            email='requester_user@email.com',
            first_name='Requester',
            last_name='User',
            username='requester_user')
        self.pi = User.objects.create(
            email='pi_user@email.com',
            first_name='PI',
            last_name='User',
            username='pi_user')
        pi_user_profile = UserProfile.objects.get(user=self.pi)
        pi_user_profile.is_pi = True
        pi_user_profile.save()

        project_status = ProjectStatusChoice.objects.get(name='Inactive')
        project = Project.objects.create(name='project', status=project_status)
        status = ProjectUserStatusChoice.objects.get(name='Active')
        pi_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')
        ProjectUser.objects.create(
            user=self.pi, project=project, role=pi_role, status=status)
        manager_role = ProjectUserRoleChoice.objects.get(name='Manager')
        ProjectUser.objects.create(
            user=requester, project=project, role=manager_role, status=status)

        create_project_allocation(project, Decimal('1000.00'))

        status = AllocationRenewalRequestStatusChoice.objects.get(
            name='Approved')
        self.request_obj = AllocationRenewalRequest.objects.create(
            requester=requester,
            pi=self.pi,
            allocation_period=self.allocation_period,
            status=status,
            pre_project=project,
            post_project=project,
            request_time=utc_now_offset_aware())

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
        num_updated = ProjectUser.objects.filter(
            project=project, user__in=[requester, pi]).update(
            role=pi_role, status=removed_status)
        self.assertEqual(num_updated, 2)

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

        project_users = ProjectUser.objects.filter(project=project)
        self.assertEqual(project_users.count(), 1)
        active_status = ProjectUserStatusChoice.objects.get(name='Active')
        project_user = project_users.first()
        self.assertEqual(project_user.user, pi)
        self.assertEqual(project_user.status, active_status)
        self.assertEqual(project_user.role.name, 'Principal Investigator')

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

    def test_runner_activates_project(self):
        """Test that the runner sets the post_project'status to
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

    def test_runner_sets_is_pi_field_of_pi_user_profile(self):
        """Test that the User designated as the PI on the request has
        the is_pi field set to True in its UserProfile."""
        pi_user_profile = UserProfile.objects.get(user=self.pi)
        pi_user_profile.is_pi = False
        pi_user_profile.save()

        num_service_units = Decimal('0.00')
        runner = AllocationRenewalProcessingRunner(
            self.request_obj, num_service_units)
        runner.run()

        pi_user_profile.refresh_from_db()
        self.assertTrue(pi_user_profile.is_pi)

    def test_runner_sets_num_service_units(self):
        """Test that the runner sets the provided number of service
        units in the request."""
        self.assertEqual(self.request_obj.num_service_units, Decimal('0.00'))

        num_service_units = Decimal('1000.00')
        runner = AllocationRenewalProcessingRunner(
            self.request_obj, num_service_units)
        runner.run()

        self.request_obj.refresh_from_db()
        self.assertEqual(self.request_obj.num_service_units, num_service_units)

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


class TestUnpooledToUnpooled(TestRunnerMixin, TestCase):
    """A class for testing the AllocationRenewalProcessingRunner in the
    'unpooled_to_unpooled' case."""

    pass


class TestUnpooledToPooled(TestRunnerMixin, TestCase):
    """A class for testing the AllocationRenewalProcessingRunner in the
    'unpooled_to_pooled' case."""

    pass


class TestPooledToPooledSame(TestRunnerMixin, TestCase):
    """A class for testing the AllocationRenewalProcessingRunner in the
    'pooled_to_pooled_same' case."""

    pass


class TestPooledToPooledDifferent(TestRunnerMixin, TestCase):
    """A class for testing the AllocationRenewalProcessingRunner in the
    'pooled_to_pooled_different' case."""

    pass


class TestPooledToUnpooledOld(TestRunnerMixin, TestCase):
    """A class for testing the AllocationRenewalProcessingRunner in the
    'pooled_to_unpooled_old' case."""

    pass


class TestPooledToUnpooledNew(TestRunnerMixin, TestCase):
    """A class for testing the AllocationRenewalProcessingRunner in the
    'pooled_to_unpooled_new' case."""

    pass
