from coldfront.api.statistics.utils import create_project_allocation
from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationAttribute
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.allocation.models import AllocationRenewalRequestStatusChoice
from coldfront.core.allocation.models import AllocationStatusChoice
from coldfront.core.allocation.utils import get_project_compute_allocation
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectAllocationRequestStatusChoice
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.project.utils import SavioProjectApprovalRunner
from coldfront.core.project.utils_.renewal_utils import AllocationRenewalProcessingRunner
from coldfront.core.resource.models import Resource
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
            # This command calls 'print', whose output must be suppressed.
            'import_field_of_science_data',
            'add_default_project_choices',
        ]
        sys.stdout = open(os.devnull, 'w')
        for command in commands:
            call_command(command, stdout=out, stderr=err)
        sys.stdout = sys.__stdout__

        self.allocation_period = AllocationPeriod.objects.get(name='AY21-22')

        # Create a requester user and multiple PI users.
        self.requester = User.objects.create(
            email='requester@email.com',
            first_name='Requester',
            last_name='User',
            username='requester')
        for i in range(4):
            username = f'pi{i}'
            user = User.objects.create(
                email=f'{username}@email.com',
                first_name=f'PI{i}',
                last_name='User',
                username=username)
            # Set self.pi{i} to the created user.
            setattr(self, username, user)
            # Set each PI's is_pi status.
            user_profile = UserProfile.objects.get(user=user)
            user_profile.is_pi = True
            user_profile.save()

        active_project_status = ProjectStatusChoice.objects.get(name='Active')
        inactive_project_status = ProjectStatusChoice.objects.get(
            name='Inactive')
        active_project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')
        manager_project_user_role = ProjectUserRoleChoice.objects.get(
            name='Manager')
        pi_project_user_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')

        # Create Projects.
        self.unpooled_project0 = Project.objects.create(
            name='unpooled_project0', status=active_project_status)
        self.unpooled_project1 = Project.objects.create(
            name='unpooled_project1', status=inactive_project_status)
        self.pooled_project0 = Project.objects.create(
            name='pooled_project0', status=active_project_status)
        self.pooled_project1 = Project.objects.create(
            name='pooled_project1', status=active_project_status)

        # Add the designated PIs to each Project.
        self.projects_and_pis = {
            self.unpooled_project0: [self.pi0],
            self.unpooled_project1: [self.pi1],
            self.pooled_project0: [self.pi0, self.pi1],
            self.pooled_project1: [self.pi2, self.pi3],
        }
        for project, pi_users in self.projects_and_pis.items():
            for pi_user in pi_users:
                ProjectUser.objects.create(
                    project=project,
                    user=pi_user,
                    role=pi_project_user_role,
                    status=active_project_user_status)
            # Add the requester as a manager on each Project.
            ProjectUser.objects.create(
                project=project,
                user=self.requester,
                role=manager_project_user_role,
                status=active_project_user_status)

        # Create a compute Allocation for each Project.
        self.project_service_units = {}
        for i, project in enumerate(self.projects_and_pis.keys()):
            value = Decimal(str(i * 1000))
            create_project_allocation(project, value)
            self.project_service_units[project] = value

        # This should be set by the subclasses.
        self.request_obj = None

    def assert_allocation_service_units_value(self, allocation, expected):
        """Assert that the given Allocation has an AllocationAttribute
        with type 'Service Units' and the given expected value."""
        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Service Units')
        kwargs = {
            'allocation_attribute_type': allocation_attribute_type,
        }
        attributes = allocation.allocationattribute_set.filter(**kwargs)
        self.assertEqual(attributes.count(), 1)
        self.assertEqual(str(expected), attributes.first().value)

    def assert_pooling_preference_case(self, expected):
        """Assert that the pooling preference case of the request_obj is
        the provided, expected one."""
        actual = self.request_obj.get_pooling_preference_case()
        self.assertEqual(expected, actual)

    def create_request(self, pi=None, pre_project=None, post_project=None,
                       new_project_request=None):
        """Create and return an AllocationRenewalRequest with the given
        parameters."""
        assert pi and pre_project and post_project
        approved_renewal_request_status = \
            AllocationRenewalRequestStatusChoice.objects.get(name='Approved')
        kwargs = {
            'requester': self.requester,
            'pi': pi,
            'allocation_period': self.allocation_period,
            'status': approved_renewal_request_status,
            'pre_project': pre_project,
            'post_project': post_project,
            'request_time': utc_now_offset_aware(),
            'new_project_request': new_project_request,
        }
        return AllocationRenewalRequest.objects.create(**kwargs)

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

    def test_runner_sets_allocation_type(self):
        """Test that the runner sets an AllocationAttribute with type
        'Savio Allocation Type' on the post_project's compute
        Allocation."""
        request = self.request_obj
        project = request.post_project
        allocation = get_project_compute_allocation(project)
        # Delete any that already exist.
        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Savio Allocation Type')
        kwargs = {
            'allocation_attribute_type': allocation_attribute_type,
        }
        allocation.allocationattribute_set.filter(**kwargs).delete()

        num_service_units = Decimal('1000.00')
        runner = AllocationRenewalProcessingRunner(request, num_service_units)
        runner.run()

        allocation.refresh_from_db()
        try:
            allocation_attribute = allocation.allocationattribute_set.get(
                **kwargs)
        except AllocationAttribute.DoesNotExist:
            self.fail('An AllocationAttribute should have been created.')
        else:
            self.assertEqual(
                allocation_attribute.value, SavioProjectAllocationRequest.FCA)

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


class TestUnpooledToUnpooled(TestRunnerMixin, TestCase):
    """A class for testing the AllocationRenewalProcessingRunner in the
    'unpooled_to_unpooled' case."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.request_obj = self.create_request(
            pi=self.pi0,
            pre_project=self.unpooled_project0,
            post_project=self.unpooled_project0)

    def test_pooling_preference_case(self):
        """Test that the pooling preference case for the class' renewal
        request is 'unpooled_to_unpooled'."""
        self.assert_pooling_preference_case(
            AllocationRenewalRequest.UNPOOLED_TO_UNPOOLED)


class TestUnpooledToPooled(TestRunnerMixin, TestCase):
    """A class for testing the AllocationRenewalProcessingRunner in the
    'unpooled_to_pooled' case."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.request_obj = self.create_request(
            pi=self.pi0,
            pre_project=self.unpooled_project0,
            post_project=self.pooled_project1)

    def test_pooling_preference_case(self):
        """Test that the pooling preference case for the class' renewal
        request is 'unpooled_to_pooled'."""
        self.assert_pooling_preference_case(
            AllocationRenewalRequest.UNPOOLED_TO_POOLED)


class TestPooledToPooledSame(TestRunnerMixin, TestCase):
    """A class for testing the AllocationRenewalProcessingRunner in the
    'pooled_to_pooled_same' case."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.request_obj = self.create_request(
            pi=self.pi0,
            pre_project=self.pooled_project0,
            post_project=self.pooled_project0)

    def test_pooling_preference_case(self):
        """Test that the pooling preference case for the class' renewal
        request is 'pooled_to_pooled_same'."""
        self.assert_pooling_preference_case(
            AllocationRenewalRequest.POOLED_TO_POOLED_SAME)


class TestPooledToPooledDifferent(TestRunnerMixin, TestCase):
    """A class for testing the AllocationRenewalProcessingRunner in the
    'pooled_to_pooled_different' case."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.request_obj = self.create_request(
            pi=self.pi0,
            pre_project=self.pooled_project0,
            post_project=self.pooled_project1)

    def test_pooling_preference_case(self):
        """Test that the pooling preference case for the class' renewal
        request is 'pooled_to_pooled_different'."""
        self.assert_pooling_preference_case(
            AllocationRenewalRequest.POOLED_TO_POOLED_DIFFERENT)


class TestPooledToUnpooledOld(TestRunnerMixin, TestCase):
    """A class for testing the AllocationRenewalProcessingRunner in the
    'pooled_to_unpooled_old' case."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.request_obj = self.create_request(
            pi=self.pi0,
            pre_project=self.pooled_project0,
            post_project=self.unpooled_project0)

    def test_pooling_preference_case(self):
        """Test that the pooling preference case for the class' renewal
        request is 'pooled_to_unpooled_old'."""
        self.assert_pooling_preference_case(
            AllocationRenewalRequest.POOLED_TO_UNPOOLED_OLD)


class TestPooledToUnpooledNew(TestRunnerMixin, TestCase):
    """A class for testing the AllocationRenewalProcessingRunner in the
    'pooled_to_unpooled_new' case."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        new_project_request = \
            self.simulate_new_project_allocation_request_processing()
        self.request_obj = self.create_request(
            pi=self.pi0,
            pre_project=self.pooled_project0,
            post_project=new_project_request.project,
            new_project_request=new_project_request)

    def simulate_new_project_allocation_request_processing(self):
        """Create a new Project and simulate its processing. Return the
        created SavioProjectAllocationRequest."""
        # Create a new Project.
        new_project_name = 'unpooled_project2'
        new_project_status = ProjectStatusChoice.objects.get(name='New')
        new_project = Project.objects.create(
            name=new_project_name,
            status=new_project_status,
            title=new_project_name,
            description=f'Description of {new_project_name}.')

        # Create a compute Allocation for the new Project.
        new_allocation_status = AllocationStatusChoice.objects.get(name='New')
        allocation = Allocation.objects.create(
            project=new_project, status=new_allocation_status)
        resource = Resource.objects.get(name='Savio Compute')
        allocation.resources.add(resource)
        allocation.save()

        # Create an 'Under Review' SavioProjectAllocationRequest for the new
        # Project.
        under_review_request_status = \
            ProjectAllocationRequestStatusChoice.objects.get(
                name='Under Review')
        new_project_request = SavioProjectAllocationRequest.objects.create(
            requester=self.requester,
            allocation_type=SavioProjectAllocationRequest.FCA,
            pi=self.pi0,
            project=new_project,
            survey_answers={},
            status=under_review_request_status)

        # Process the request.
        num_service_units = Decimal('1000.00')
        runner = SavioProjectApprovalRunner(
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
