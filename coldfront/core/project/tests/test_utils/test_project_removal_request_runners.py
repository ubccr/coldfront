from unittest.mock import patch

from django.core import mail

from coldfront.api.statistics.utils import create_project_allocation
from coldfront.api.statistics.utils import create_user_project_allocation
from coldfront.core.project.models import *
from coldfront.core.project.utils_.removal_utils import ProjectRemovalRequestRunner
from coldfront.core.project.utils_.removal_utils import ProjectRemovalRequestProcessingRunner
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.user.models import *
from coldfront.core.allocation.models import *
from coldfront.core.utils.tests.test_base import TestBase


def raise_exception(*args, **kwargs):
    """Raise an exception."""
    raise Exception('Test exception.')


class TestRemovalRequestRunnerBase(TestBase):
    """A base testing class for removal request runners."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

        # Create three normal users.
        for i in range(3):
            user = User.objects.create(
                email=f'user{i+1}@email.com',
                first_name='Normal',
                last_name=f'User{i+1}',
                username=f'user{i+1}'
            )
            setattr(self, f'user{i+1}', user)

        # Create two PIs.

        for i in range(2):
            pi = User.objects.create(
                email=f'pi{i+1}@email.com',
                first_name=f'Pi{i+1}',
                last_name=f'User',
                username=f'pi{i+1}')
            setattr(self, f'pi{i+1}', pi)
            user_profile = UserProfile.objects.get(user=pi)
            user_profile.is_pi = True
            user_profile.save()

        self.manager = User.objects.create(
            email='manager@email.com',
            first_name='Manager',
            last_name='User',
            username='manager')

        for user in User.objects.all():
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

        # Create a compute allocation for the Project.
        sus = Decimal('1000.00')
        create_project_allocation(self.project1, sus)

        # Add users to project and create allocation users.
        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Cluster Account Status')
        for user in [self.user1, self.user2, self.user3]:
            ProjectUser.objects.create(
                project=self.project1,
                user=user,
                role=user_project_role,
                status=active_project_user_status)

            objects = create_user_project_allocation(
                user, self.project1, sus)
            allocation = objects.allocation
            allocation_user = objects.allocation_user
            AllocationUserAttribute.objects.create(
                allocation_attribute_type=allocation_attribute_type,
                allocation=allocation,
                allocation_user=allocation_user,
                value='Active')

        # Clear the mail outbox.
        mail.outbox = []


class TestProjectRemovalRequestRunner(TestRemovalRequestRunnerBase):
    """A testing class for ProjectRemovalRequestRunner."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

    def test_normal_user_self_removal_request(self):
        """
        Testing when a single user self requests to be removed
        """

        # Test project user status before removal
        self.assertEqual(self.project1.projectuser_set.get(
            user=self.user1).status.name,
                         'Active')

        request_runner = ProjectRemovalRequestRunner(
            self.user1, self.user1, self.project1)
        removal_request = request_runner.run()
        success_messages, error_messages = request_runner.get_messages()

        # testing if a removal request was made
        self.assertIsNotNone(removal_request)

        # testing removal request attributes
        self.assertEqual(removal_request.project_user,
                         self.project1.projectuser_set.get(user=self.user1))
        self.assertEqual(removal_request.requester, self.user1)
        self.assertIsNone(removal_request.completion_time)
        self.assertEqual(removal_request.status.name, 'Pending')

        # check messages
        test_message = f'Successfully created project removal request for ' \
                       f'user {self.user1.username}.'
        self.assertEqual(success_messages[0], test_message)
        self.assertEqual(len(success_messages), 1)
        self.assertEqual(len(error_messages), 0)

        # Test project user status
        self.assertEqual(self.project1.projectuser_set.get(
            user=self.user1).status.name,
                         'Pending - Remove')

        # send email to admins, pis and managers for self removal
        request_runner.send_emails()
        manager_pi_queryset = self.project1.projectuser_set.filter(
            role__name__in=['Manager', 'Principal Investigator'],
            status__name='Active').exclude(user=removal_request.requester)

        email_to_list = [proj_user.user.email for proj_user in manager_pi_queryset]
        self.assertEqual(len(mail.outbox), len(manager_pi_queryset) + 1)

        email_body = f'{self.user1.first_name} {self.user1.last_name} of ' \
                     f'Project {self.project1.name} has requested to remove ' \
                     f'{self.user1.first_name} {self.user1.last_name} ' \
                     f'from {self.project1.name}'
        email_body_admin = f'There is a new request to remove ' \
                           f'{self.user1.first_name} {self.user1.last_name} ' \
                           f'from {self.project1.name}.'

        for email in mail.outbox:
            if email.to[0] in settings.EMAIL_ADMIN_LIST:
                self.assertIn(email_body_admin, email.body)
            else:
                self.assertIn(email_body, email.body)
                self.assertIn(email.to[0], email_to_list)
            self.assertEqual(settings.EMAIL_SENDER, email.from_email)

        # Test creating another project removal request after self removal request
        request_runner = ProjectRemovalRequestRunner(
            self.pi1, self.user1, self.project1)
        removal_request = request_runner.run()
        success_messages, error_messages = request_runner.get_messages()

        # testing if a removal request was made
        self.assertIsNone(removal_request)

        # check messages
        test_message = f'Error requesting removal of user {self.user1.username}. ' \
                       f'An active project removal request for user ' \
                       f'{self.user1.username} already exists.'
        self.assertEqual(error_messages[0], test_message)
        self.assertEqual(len(success_messages), 0)
        self.assertEqual(len(error_messages), 1)

    def test_normal_user_pi_removal_request(self):
        """
        Testing when a pi requests for a normal user to be removed
        """

        # Test project user status before removal
        self.assertEqual(self.project1.projectuser_set.get(
            user=self.user1).status.name,
                         'Active')

        request_runner = ProjectRemovalRequestRunner(
            self.pi1, self.user1, self.project1)
        removal_request = request_runner.run()
        success_messages, error_messages = request_runner.get_messages()

        # testing if a removal request was made
        self.assertIsNotNone(removal_request)

        # testing removal request attributes
        self.assertEqual(removal_request.project_user,
                         self.project1.projectuser_set.get(user=self.user1))
        self.assertEqual(removal_request.requester, self.pi1)
        self.assertIsNone(removal_request.completion_time)
        self.assertEqual(removal_request.status.name, 'Pending')

        # check messages
        test_message = f'Successfully created project removal request for ' \
                       f'user {self.user1.username}.'
        self.assertEqual(success_messages[0], test_message)
        self.assertEqual(len(success_messages), 1)
        self.assertEqual(len(error_messages), 0)

        # Test project user status
        self.assertEqual(self.project1.projectuser_set.get(
            user=self.user1).status.name,
                         'Pending - Remove')

        # send email to admins, pis and managers for self removal
        request_runner.send_emails()
        manager_pi_queryset = self.project1.projectuser_set.filter(
            role__name__in=['Manager', 'Principal Investigator'],
            status__name='Active').exclude(user=removal_request.requester)

        email_to_list = [proj_user.user.email for proj_user in manager_pi_queryset]\
                        + [self.user1.email]
        self.assertEqual(len(mail.outbox), len(manager_pi_queryset) + 2)

        email_body = f'{self.pi1.first_name} {self.pi1.last_name} of ' \
                     f'Project {self.project1.name} has requested to remove ' \
                     f'{self.user1.first_name} {self.user1.last_name} ' \
                     f'from {self.project1.name}'
        email_body_admin = f'There is a new request to remove ' \
                           f'{self.user1.first_name} {self.user1.last_name} ' \
                           f'from {self.project1.name}.'

        for email in mail.outbox:
            if email.to[0] in settings.EMAIL_ADMIN_LIST:
                self.assertIn(email_body_admin, email.body)
            else:
                self.assertIn(email_body, email.body)
                self.assertIn(email.to[0], email_to_list)
            self.assertEqual(settings.EMAIL_SENDER, email.from_email)

        # Test creating another project removal request after pi removal request
        request_runner = ProjectRemovalRequestRunner(
            self.pi1, self.user1, self.project1)
        removal_request = request_runner.run()
        success_messages, error_messages = request_runner.get_messages()

        # testing if a removal request was made
        self.assertIsNone(removal_request)

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
        self.assertEqual(self.project1.projectuser_set.get(
            user=self.pi1).status.name,
                         'Active')

        request_runner = ProjectRemovalRequestRunner(
            self.pi1, self.pi1, self.project1)
        removal_request = request_runner.run()
        success_messages, error_messages = request_runner.get_messages()

        # testing if a removal request was made
        self.assertIsNone(removal_request)

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
        self.assertEqual(self.project1.projectuser_set.get(
            user=self.manager).status.name,
                         'Active')

        request_runner = ProjectRemovalRequestRunner(
            self.manager, self.manager, self.project1)
        removal_request = request_runner.run()
        success_messages, error_messages = request_runner.get_messages()

        # testing if a removal request was made
        self.assertIsNone(removal_request)

        # check messages
        test_message = f'Error requesting removal of user {self.manager.username}. ' \
                       f'Cannot remove the only manager in a project.'
        self.assertEqual(error_messages[0], test_message)
        self.assertEqual(len(success_messages), 0)
        self.assertEqual(len(error_messages), 1)

        # test project user status after failed removal request
        self.assertEqual(self.project1.projectuser_set.get(
            user=self.manager).status.name,
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
        self.assertEqual(self.project1.projectuser_set.get(
            user=self.user1).status.name,
                         'Active')

        request_runner = ProjectRemovalRequestRunner(
            self.user1, self.user1, self.project1)
        removal_request = request_runner.run()
        success_messages, error_messages = request_runner.get_messages()

        # testing if a removal request was made
        self.assertIsNotNone(removal_request)

        # testing removal request attributes
        self.assertEqual(removal_request.project_user,
                         self.project1.projectuser_set.get(user=self.user1))
        self.assertEqual(removal_request.requester, self.user1)
        self.assertIsNone(removal_request.completion_time)
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

    def test_manager_removal_request_given_multiple_managers(self):
        """
        Testing when a PI requests to remove a manager given that
        there are multuple managers
        """

        manager2 = User.objects.create(
            email='manager2@email.com',
            first_name='Manager2',
            last_name='User',
            username='manager2')

        manager3 = User.objects.create(
            email='manager2@email.com',
            first_name='Manager3',
            last_name='User',
            username='manager3')

        active_project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')
        manager_project_role = ProjectUserRoleChoice.objects.get(
            name='Manager')

        for manager in [manager2, manager3]:
            ProjectUser.objects.create(
                project=self.project1,
                user=manager,
                role=manager_project_role,
                status=active_project_user_status)

        self.assertEqual(self.project1.projectuser_set.get(
            user=self.user1).status.name,
                         'Active')

        request_runner = ProjectRemovalRequestRunner(
            self.pi1, manager2, self.project1)
        removal_request = request_runner.run()
        success_messages, error_messages = request_runner.get_messages()

        # testing if a removal request was made
        self.assertIsNotNone(removal_request)

        # testing removal request attributes
        self.assertEqual(removal_request.project_user,
                         self.project1.projectuser_set.get(user=manager2))
        self.assertEqual(removal_request.requester, self.pi1)
        self.assertIsNone(removal_request.completion_time)
        self.assertEqual(removal_request.status.name, 'Pending')

        # check messages
        test_message = f'Successfully created project removal request for ' \
                       f'user {manager2.username}.'
        self.assertEqual(success_messages[0], test_message)
        self.assertEqual(len(success_messages), 1)
        self.assertEqual(len(error_messages), 0)

        # Test project user status
        self.assertEqual(self.project1.projectuser_set.get(user=manager2).status.name,
                         'Pending - Remove')

        # send email to admins, pis and managers for self removal
        request_runner.send_emails()
        manager_pi_queryset = self.project1.projectuser_set.filter(
            role__name__in=['Manager', 'Principal Investigator'],
            status__name='Active').exclude(user=removal_request.requester)

        email_to_list = [proj_user.user.email for proj_user in manager_pi_queryset]
        self.assertEqual(len(mail.outbox), len(manager_pi_queryset) + 2)

        email_body = f'{self.pi1.first_name} {self.pi1.last_name} of ' \
                     f'Project {self.project1.name} has requested to remove ' \
                     f'{manager2.first_name} {manager2.last_name} ' \
                     f'from {self.project1.name}'
        email_body_admin = f'There is a new request to remove ' \
                           f'{manager2.first_name} {manager2.last_name} ' \
                           f'from {self.project1.name}.'

        for email in mail.outbox:
            if email.to[0] in settings.EMAIL_ADMIN_LIST:
                self.assertIn(email_body_admin, email.body)
            else:
                self.assertIn(email_body, email.body)
                self.assertIn(email.to[0], email_to_list)
            self.assertEqual(settings.EMAIL_SENDER, email.from_email)

        # Test creating another project removal request after pi removal request
        request_runner = ProjectRemovalRequestRunner(
            self.pi1, manager2, self.project1)
        removal_request = request_runner.run()
        success_messages, error_messages = request_runner.get_messages()

        # testing if a removal request was made
        self.assertIsNone(removal_request)

        # check messages
        test_message = f'Error requesting removal of user {manager2.username}. ' \
                       f'An active project removal request for user ' \
                       f'{manager2.username} already exists.'
        self.assertEqual(error_messages[0], test_message)
        self.assertEqual(len(success_messages), 0)
        self.assertEqual(len(error_messages), 1)

    def test_normal_user_self_removal_request_pi_no_notifications(self):
        """
        Testing when a single user self requests to be removed and the PI
        has enable_notifications=False
        """

        self.pi1.enable_notifications = False
        self.pi1.save()

        self.assertFalse(self.pi1.enable_notifications)

        # Test project user status before removal
        self.assertEqual(self.project1.projectuser_set.get(
            user=self.user1).status.name,
                         'Active')

        request_runner = ProjectRemovalRequestRunner(
            self.user1, self.user1, self.project1)
        removal_request = request_runner.run()
        success_messages, error_messages = request_runner.get_messages()

        # testing if a removal request was made
        self.assertIsNotNone(removal_request)

        # testing removal request attributes
        self.assertEqual(removal_request.project_user,
                         self.project1.projectuser_set.get(user=self.user1))
        self.assertEqual(removal_request.requester, self.user1)
        self.assertIsNone(removal_request.completion_time)
        self.assertEqual(removal_request.status.name, 'Pending')

        # check messages
        test_message = f'Successfully created project removal request for ' \
                       f'user {self.user1.username}.'
        self.assertEqual(success_messages[0], test_message)
        self.assertEqual(len(success_messages), 1)
        self.assertEqual(len(error_messages), 0)

        # Test project user status
        self.assertEqual(self.project1.projectuser_set.get(
            user=self.user1).status.name,
                         'Pending - Remove')

        # send email to admins, pis and managers for self removal
        request_runner.send_emails()
        manager_pi_queryset = self.project1.projectuser_set.filter(
            role__name__in=['Manager', 'Principal Investigator'],
            status__name='Active',
            enable_notifications=True).exclude(user=removal_request.requester)

        email_to_list = [proj_user.user.email for proj_user in manager_pi_queryset]
        self.assertEqual(len(mail.outbox), len(manager_pi_queryset) + 1)

        email_body = f'{self.user1.first_name} {self.user1.last_name} of ' \
                     f'Project {self.project1.name} has requested to remove ' \
                     f'{self.user1.first_name} {self.user1.last_name} ' \
                     f'from {self.project1.name}'
        email_body_admin = f'There is a new request to remove ' \
                           f'{self.user1.first_name} {self.user1.last_name} ' \
                           f'from {self.project1.name}.'

        for email in mail.outbox:
            if email.to[0] in settings.EMAIL_ADMIN_LIST:
                self.assertIn(email_body_admin, email.body)
            else:
                self.assertIn(email_body, email.body)
                self.assertIn(email.to[0], email_to_list)
            self.assertNotEqual(email.to, self.pi1.email)
            self.assertEqual(settings.EMAIL_SENDER, email.from_email)


class TestProjectRemovalRequestProcessingRunner(TestRemovalRequestRunnerBase):
    """A class for testing ProjectRemovalRequestProcessingRunner."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

        self._module = 'coldfront.core.project.utils_.removal_utils'

        request_runner = ProjectRemovalRequestRunner(
            self.pi1, self.user1, self.project1)
        self.request_obj = request_runner.run()
        self.request_obj.status = \
            ProjectUserRemovalRequestStatusChoice.objects.get(
                name='Complete')
        self.request_obj.completion_time = utc_now_offset_aware()
        self.request_obj.save()

        self.complete_status = \
            ProjectUserRemovalRequestStatusChoice.objects.get(name='Complete')
        self.project_user_obj = ProjectUser.objects.get(
            project=self.project1, user=self.user1)
        self.project_user_obj.status = ProjectUserStatusChoice.objects.get(
            name='Pending - Remove')
        self.project_user_obj.save()
        self.allocation_user_obj = AllocationUser.objects.get(
            allocation__project=self.project_user_obj.project, user=self.user1)
        self.allocation_user_attribute_obj = \
            self.allocation_user_obj.allocationuserattribute_set.get(
                allocation_attribute_type__name='Cluster Account Status')

        # Disable email notifications for one PI.
        ProjectUser.objects.filter(user=self.pi2).update(
            enable_notifications=False)

    def _assert_emails_sent(self):
        """Assert that emails are sent from the expected sender to the
        expected recipients, with the expected body."""
        expected_from = settings.EMAIL_SENDER
        expected_to = {
            user.email for user in [self.user1, self.pi1, self.manager]}
        user_name = f'{self.user1.first_name} {self.user1.last_name}'
        pi_name = f'{self.pi1.first_name} {self.pi1.last_name}'
        project_name = self.project1.name
        expected_body = (
            f'The request to remove {user_name} of Project {project_name} '
            f'initiated by {pi_name} has been completed. {user_name} is no '
            f'longer a user of Project {project_name}.')

        for email in mail.outbox:
            self.assertEqual(email.from_email, expected_from)
            self.assertEqual(len(email.to), 1)
            to = email.to[0]
            self.assertIn(to, expected_to)
            expected_to.remove(to)
            self.assertIn(expected_body, email.body)

        self.assertFalse(expected_to)

    def _assert_post_state(self):
        """Assert that the relevant objects have the expected state,
        assuming that the runner has run successfully."""
        self._refresh_objects()
        self.assertEqual(self.project_user_obj.status.name, 'Removed')
        self.assertEqual(self.allocation_user_obj.status.name, 'Removed')
        self.assertEqual(self.allocation_user_attribute_obj.value, 'Denied')

    def _assert_pre_state(self):
        """Assert that the relevant objects have the expected state,
        assuming that the runner has either not run or not run
        successfully."""
        self._refresh_objects()
        self.assertEqual(self.project_user_obj.status.name, 'Pending - Remove')
        self.assertEqual(self.allocation_user_obj.status.name, 'Active')
        self.assertEqual(self.allocation_user_attribute_obj.value, 'Active')

    def _refresh_objects(self):
        """Refresh relevant objects from the database."""
        self.project_user_obj.refresh_from_db()
        self.allocation_user_obj.refresh_from_db()
        self.allocation_user_attribute_obj.refresh_from_db()

    def test_allocation_user_attribute_missing_allowed(self):
        """Test that, when the ProjectUser's has no associated
        AllocationUserAttribute, the runner proceeds without error."""
        self.assertEqual(len(mail.outbox), 0)

        self._assert_pre_state()

        self.allocation_user_attribute_obj.delete()

        runner = ProjectRemovalRequestProcessingRunner(self.request_obj)
        with self.assertLogs(self._module, 'INFO') as cm:
            runner.run()

        self.project_user_obj.refresh_from_db()
        self.allocation_user_obj.refresh_from_db()
        self.assertEqual(self.project_user_obj.status.name, 'Removed')
        self.assertEqual(self.allocation_user_obj.status.name, 'Removed')

        self.assertGreater(len(cm.output), 0)
        self._assert_emails_sent()

        self.assertGreater(len(runner.get_warning_messages()), 0)

    def test_allocation_user_missing_allowed(self):
        """Test that, when the ProjectUser has no associated
        AllocationUser, the runner proceeds without error."""
        self.assertEqual(len(mail.outbox), 0)

        self._assert_pre_state()

        self.allocation_user_obj.delete()

        runner = ProjectRemovalRequestProcessingRunner(self.request_obj)
        with self.assertLogs(self._module, 'INFO') as cm:
            runner.run()

        self.project_user_obj.refresh_from_db()
        self.assertEqual(self.project_user_obj.status.name, 'Removed')

        self.assertGreater(len(cm.output), 0)
        self._assert_emails_sent()

        self.assertGreater(len(runner.get_warning_messages()), 0)

    def test_asserts_input_request(self):
        """Test that the runner asserts that the request has the
        expected type and status."""
        with self.assertRaises(AssertionError):
            ProjectRemovalRequestProcessingRunner(0)

        invalid_statuses = \
            ProjectUserRemovalRequestStatusChoice.objects.exclude(
                pk=self.complete_status.pk)
        self.assertGreater(invalid_statuses.count(), 0)
        for status in invalid_statuses:
            self.request_obj.status = status
            self.request_obj.save()
            with self.assertRaises(AssertionError):
                ProjectRemovalRequestProcessingRunner(self.request_obj)

        self.request_obj.status = self.complete_status
        self.request_obj.save()
        ProjectRemovalRequestProcessingRunner(self.request_obj)

    def test_email_failure_no_rollback(self):
        """Test that, when an exception is raised when attempting to
        send an email, changes made so far are not rolled back because
        such an exception is caught."""
        self.assertEqual(len(mail.outbox), 0)

        self._assert_pre_state()

        with patch.object(
                ProjectRemovalRequestProcessingRunner,
                '_send_emails',
                raise_exception):
            runner = ProjectRemovalRequestProcessingRunner(self.request_obj)
            with self.assertLogs(self._module, 'INFO') as log_cm:
                runner.run()

        self._assert_post_state()

        self.assertGreater(len(log_cm.output), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_exception_inside_transaction_rollback(self):
        """Test that, when an exception is raised inside the
        transaction, changes made so far are rolled back."""
        self.assertEqual(len(mail.outbox), 0)

        self._assert_pre_state()

        with patch.object(
                ProjectRemovalRequestProcessingRunner,
                '_remove_user_from_project_compute_allocation',
                raise_exception):
            runner = ProjectRemovalRequestProcessingRunner(self.request_obj)
            # TODO: Assert that logs were not written. Python 3.10 has an
            # TODO: assertNotLogs method.
            with self.assertRaises(Exception) as cm:
                runner.run()
            self.assertEqual(str(cm.exception), 'Test exception.')

        self._assert_pre_state()

        self.assertEqual(len(mail.outbox), 0)

    def test_exception_outside_transaction_no_rollback(self):
        """Test that, when an exception is raised outside the
        transaction, changes made so far are not rolled back."""
        self.assertEqual(len(mail.outbox), 0)

        self._assert_pre_state()

        with patch.object(
                ProjectRemovalRequestProcessingRunner,
                '_send_emails_safe',
                raise_exception):
            runner = ProjectRemovalRequestProcessingRunner(self.request_obj)
            with self.assertLogs(self._module, 'INFO') as log_cm:
                with self.assertRaises(Exception) as exc_cm:
                    runner.run()
            self.assertEqual(str(exc_cm.exception), 'Test exception.')

        self._assert_post_state()

        self.assertGreater(len(log_cm.output), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_success(self):
        """Test that the runner removes the user from the Project,
        removes the user from the associated 'CLUSTER_NAME Compute'
        Allocation, updates the associated 'Cluster Account Status'
        AllocationUserAttribute, writes to the log, and sends emails."""
        self.assertEqual(len(mail.outbox), 0)

        self._assert_pre_state()

        runner = ProjectRemovalRequestProcessingRunner(self.request_obj)
        with self.assertLogs(self._module, 'INFO') as cm:
            runner.run()

        self._assert_post_state()

        self.assertGreater(len(cm.output), 0)
        self._assert_emails_sent()

        self.assertFalse(runner.get_warning_messages())
