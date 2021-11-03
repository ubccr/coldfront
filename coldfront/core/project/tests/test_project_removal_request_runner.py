from coldfront.api.statistics.utils import create_project_allocation
from coldfront.core.project.models import *
from coldfront.core.project.utils import ProjectRemovalRequestRunner
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.user.models import *
from coldfront.core.allocation.models import *

from django.test import override_settings, TestCase
from django.contrib.auth.models import User
from django.core import mail
from django.core.management import call_command

from decimal import Decimal
from io import StringIO
import os
import sys


class TestRunnerMixin(TestCase):
    """A mixin for testing AllocationRenewalProcessingRunner."""

    def setUp(self):
        """Set up test data."""
        out, err = StringIO(), StringIO()
        commands = [
            'add_resource_defaults',
            'add_allocation_defaults',
            'import_field_of_science_data',
            'add_default_project_choices',
            'create_project_removal_request_statuses',
        ]
        sys.stdout = open(os.devnull, 'w')
        for command in commands:
            call_command(command, stdout=out, stderr=err)
        sys.stdout = sys.__stdout__

        # Create a requester user and multiple PI users.
        self.user1 = User.objects.create(
            email='user1@email.com',
            first_name='Normal',
            last_name='User1',
            username='user1')

        self.user2 = User.objects.create(
            email='user2@email.com',
            first_name='Normal',
            last_name='User2',
            username='user2')

        self.pi1 = User.objects.create(
            email='pi1@email.com',
            first_name='Pi1',
            last_name='User',
            username='pi1')
        user_profile = UserProfile.objects.get(user=self.pi1)
        user_profile.is_pi = True
        user_profile.save()

        self.pi2 = User.objects.create(
            email='pi2@email.com',
            first_name='Pi2',
            last_name='User',
            username='pi2')
        user_profile = UserProfile.objects.get(user=self.pi2)
        user_profile.is_pi = True
        user_profile.save()

        self.manager = User.objects.create(
            email='manager@email.com',
            first_name='Manager',
            last_name='User',
            username='manager')

        for user in [self.user1, self.user2, self.pi1, self.pi2, self.manager]:
            user_profile = UserProfile.objects.get(user=user)
            user_profile.access_agreement_signed_date = utc_now_offset_aware()
            user_profile.save()

        active_project_status = ProjectStatusChoice.objects.get(name='Active')
        active_project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')
        manager_project_role = ProjectUserRoleChoice.objects.get(
            name='Manager')
        pi_project_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')
        user_project_role = ProjectUserRoleChoice.objects.get(
            name='User')

        # Create Projects.
        self.project1 = Project.objects.create(
            name='project1', status=active_project_status)

        # add pis
        for pi_user in [self.pi1, self.pi2]:
            ProjectUser.objects.create(
                project=self.project1,
                user=pi_user,
                role=pi_project_role,
                status=active_project_user_status)

        # Add the manager to project1.
        ProjectUser.objects.create(
            project=self.project1,
            user=self.manager,
            role=manager_project_role,
            status=active_project_user_status)

        # add users to project
        for user in [self.user1, self.user2]:
            ProjectUser.objects.create(
                project=self.project1,
                user=user,
                role=user_project_role,
                status=active_project_user_status)

        # # Create a compute Allocation for each Project.
        # self.project_service_units = {}
        # self.projects_and_allocations = {}
        #
        # value = Decimal(str(1000))
        # allocation = create_project_allocation(self.project1, value).allocation
        # self.project_service_units[self.project1] = value
        # self.projects_and_allocations[self.project1] = allocation
        #
        # # Create AllocationUsers on the compute Allocation.
        # active_allocation_user_status = AllocationUserStatusChoice.objects.get(
        #     name='Active')
        #
        # allocation = self.projects_and_allocations[self.project1]
        # for pi_user in [self.pi1, self.pi2]:
        #     AllocationUser.objects.create(
        #         allocation=allocation,
        #         user=pi_user,
        #         status=active_allocation_user_status)

        # Clear the mail outbox.
        mail.outbox = []

    def test_normal_user_self_removal_request(self):
        """
        Testing when a single user self requests to be removed
        """

        # Test project user status before removal
        self.assertEqual(self.project1.projectuser_set.get(user=self.user1).status.name,
                         'Active')

        request_runner = ProjectRemovalRequestRunner(
            self.user1, self.user1, self.project1)
        removal_request = request_runner.run()
        success_messages, error_messages = request_runner.get_messages()

        # testing if a removal request was made
        self.assertNotEqual(removal_request, None)

        # testing removal request attributes
        self.assertEqual(removal_request.project_user,
                         self.project1.projectuser_set.get(user=self.user1))
        self.assertEqual(removal_request.requester, self.user1)
        self.assertEqual(removal_request.completion_time, None)
        self.assertEqual(removal_request.status.name, 'Pending')

        # check messages
        test_message = f'Successfully created project removal request for ' \
                       f'user {self.user1.username}.'
        self.assertEqual(success_messages[0], test_message)
        self.assertEqual(len(success_messages), 1)
        self.assertEqual(len(error_messages), 0)

        # Test project user status
        self.assertEqual(self.project1.projectuser_set.get(user=self.user1).status.name,
                         'Pending - Remove')

        # Test creating another project removal request after self removal request
        request_runner = ProjectRemovalRequestRunner(
            self.pi1, self.user1, self.project1)
        removal_request = request_runner.run()
        success_messages, error_messages = request_runner.get_messages()

        # testing if a removal request was made
        self.assertEqual(removal_request, None)

        # check messages
        test_message = f'Error requesting removal of user {self.user1.username}. ' \
                       f'An active project removal request for user ' \
                       f'{self.user1.username} already exists.'
        self.assertEqual(error_messages[0], test_message)
        self.assertEqual(len(success_messages), 0)
        self.assertEqual(len(error_messages), 1)

    def test_pi_self_removal_request(self):
        """
        Testing when a PI self requests to be removed
        """

        # Test project user status before removal
        self.assertEqual(self.project1.projectuser_set.get(user=self.pi1).status.name,
                         'Active')

        request_runner = ProjectRemovalRequestRunner(
            self.pi1, self.pi1, self.project1)
        removal_request = request_runner.run()
        success_messages, error_messages = request_runner.get_messages()

        # testing if a removal request was made
        self.assertEqual(removal_request, None)

        # check messages
        test_message = f'Error requesting removal of user {self.pi1.username}. ' \
                       f'PIs cannot request to leave their project.'
        self.assertEqual(error_messages[0], test_message)
        self.assertEqual(len(success_messages), 0)
        self.assertEqual(len(error_messages), 1)

        # test project user status after failed removal request
        self.assertEqual(self.project1.projectuser_set.get(user=self.pi1).status.name,
                         'Active')

    def test_single_manager_self_removal_request(self):
        """
        Testing when a single manager self requests to be removed
        """

        # Test project user status before removal
        self.assertEqual(self.project1.projectuser_set.get(user=self.manager).status.name,
                         'Active')

        request_runner = ProjectRemovalRequestRunner(
            self.manager, self.manager, self.project1)
        removal_request = request_runner.run()
        success_messages, error_messages = request_runner.get_messages()

        # testing if a removal request was made
        self.assertEqual(removal_request, None)

        # check messages
        test_message = f'Error requesting removal of user {self.manager.username}. ' \
                       f'Cannot remove the only manager in a project.'
        self.assertEqual(error_messages[0], test_message)
        self.assertEqual(len(success_messages), 0)
        self.assertEqual(len(error_messages), 1)

        # test project user status after failed removal request
        self.assertEqual(self.project1.projectuser_set.get(user=self.manager).status.name,
                         'Active')

    def test_removal_request_given_completed_request(self):
        """
        Testing when a PI requests a user to be removed given that the
        user has a past completed removal request for the project
        """

        # Create completed removal request
        completed_removal_request = ProjectUserRemovalRequest.objects.create(
            project_user=self.project1.projectuser_set.get(user=self.user1),
            requester=self.pi1,
            completion_time=datetime.datetime.now(datetime.timezone.utc),
            status=ProjectUserRemovalRequestStatusChoice.objects.get(name='Complete')
        )

        # Test project user status before removal
        self.assertEqual(self.project1.projectuser_set.get(user=self.user1).status.name,
                         'Active')

        request_runner = ProjectRemovalRequestRunner(
            self.user1, self.user1, self.project1)
        removal_request = request_runner.run()
        success_messages, error_messages = request_runner.get_messages()

        # testing if a removal request was made
        self.assertNotEqual(removal_request, None)

        # testing removal request attributes
        self.assertEqual(removal_request.project_user,
                         self.project1.projectuser_set.get(user=self.user1))
        self.assertEqual(removal_request.requester, self.user1)
        self.assertEqual(removal_request.completion_time, None)
        self.assertEqual(removal_request.status.name, 'Pending')

        # check messages
        test_message = f'Successfully created project removal request for ' \
                       f'user {self.user1.username}.'
        self.assertEqual(success_messages[0], test_message)
        self.assertEqual(len(success_messages), 1)
        self.assertEqual(len(error_messages), 0)

        # Test project user status
        self.assertEqual(self.project1.projectuser_set.get(user=self.user1).status.name,
                         'Pending - Remove')