from http import HTTPStatus
from unittest.mock import patch

from django.contrib import messages
from django.contrib.auth.models import Permission
from django.contrib.messages import get_messages
from django.core import mail
from django.urls import reverse

from coldfront.core.allocation.models import *
from coldfront.core.project.models import *
from coldfront.core.project.utils_.removal_utils import ProjectRemovalRequestProcessingRunner
from coldfront.core.project.utils_.removal_utils import ProjectRemovalRequestRunner
from coldfront.api.statistics.utils import create_project_allocation
from coldfront.api.statistics.utils import create_user_project_allocation
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import TestBase as AllTestsBase
from coldfront.core.user.models import *


def raise_exception(*args, **kwargs):
    """Raise an exception."""
    raise Exception('Test exception.')


class TestBase(AllTestsBase):
    """Base class for testing project removal request views"""

    def setUp(self):
        """Set up test data."""
        super().setUp()

        # Create a requester user and multiple PI users.
        self.user1 = User.objects.create(
            email='user1@email.com',
            first_name='Normal',
            last_name='User1',
            username='user1')
        self.user1.set_password(self.password)
        self.user1.save()

        self.user2 = User.objects.create(
            email='user2@email.com',
            first_name='Normal',
            last_name='User2',
            username='user2')
        self.user2.set_password(self.password)
        self.user2.save()

        self.pi1 = User.objects.create(
            email='pi1@email.com',
            first_name='Pi1',
            last_name='User',
            username='pi1')
        self.pi1.set_password(self.password)
        self.pi1.save()
        user_profile = UserProfile.objects.get(user=self.pi1)
        user_profile.is_pi = True
        user_profile.save()

        self.pi2 = User.objects.create(
            email='pi2@email.com',
            first_name='Pi2',
            last_name='User',
            username='pi2')
        self.pi2.set_password(self.password)
        self.pi2.save()
        user_profile = UserProfile.objects.get(user=self.pi2)
        user_profile.is_pi = True
        user_profile.save()

        self.manager1 = User.objects.create(
            email='manager1@email.com',
            first_name='Manager1',
            last_name='User',
            username='manager1')
        self.manager1.set_password(self.password)
        self.manager1.save()

        for user in [self.user1, self.user2, self.pi1, self.pi2, self.manager1]:
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
        self.fc_project1 = Project.objects.create(
            name='fc_project1', status=active_project_status)

        # add pis
        for pi_user in [self.pi1, self.pi2]:
            ProjectUser.objects.create(
                project=self.fc_project1,
                user=pi_user,
                role=pi_project_role,
                status=active_project_user_status)

        # Add the manager to project1.
        ProjectUser.objects.create(
            project=self.fc_project1,
            user=self.manager1,
            role=manager_project_role,
            status=active_project_user_status)

        # add users to project
        for user in [self.user1, self.user2]:
            ProjectUser.objects.create(
                project=self.fc_project1,
                user=user,
                role=user_project_role,
                status=active_project_user_status)

        num_service_units = Decimal('0.00')
        create_project_allocation(self.fc_project1, num_service_units)
        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Cluster Account Status')

        for user in [self.user1, self.user2, self.pi1, self.pi2, self.manager1]:
            objects = create_user_project_allocation(
                user, self.fc_project1, num_service_units)
            allocation = objects.allocation
            allocation_user = objects.allocation_user
            AllocationUserAttribute.objects.create(
                allocation_attribute_type=allocation_attribute_type,
                allocation=allocation,
                allocation_user=allocation_user,
                value='Active')

        # Clear the mail outbox.
        mail.outbox = []


class TestProjectRemoveSelf(TestBase):
    """A class for testing Project Removal Views."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

    def test_permissions_remove_self(self):
        """Test that the correct users have permissions to perform POST
        requests for ProjectRemoveSelf view."""

        def assert_has_access(user, has_access=True, expected_messages=[]):
            """Assert that the given user has or does not have access to
            the URL. Optionally assert that any messages were sent to
            the user."""
            self.client.login(username=user.username, password=self.password)
            url = reverse(
                'project-remove-self', kwargs={'pk': self.fc_project1.pk})
            status_code = HTTPStatus.FOUND if has_access else HTTPStatus.FORBIDDEN
            response = self.client.post(url, {})
            if expected_messages:
                actual_messages = self.get_message_strings(response)
                for message in expected_messages:
                    self.assertIn(message, actual_messages)
            self.assertEqual(response.status_code, status_code)
            self.client.logout()

        # Superusers should have access.
        self.user1.is_superuser = True
        self.user1.save()
        self.assertTrue(self.user1.is_superuser)
        assert_has_access(self.user1, True)
        self.user1.is_superuser = False
        self.user1.save()
        self.assertFalse(self.user1.is_superuser)

        # normal users should have access
        assert_has_access(self.user2, True)

        # user that already requested removal should not have access
        assert_has_access(self.user1, False)

        # PIs should not have access
        assert_has_access(self.pi1, False)
        assert_has_access(self.pi2, False)

        # single manager should not have access
        assert_has_access(self.manager1, False)

        # if there are multiple managers, they should have access
        self.manager2 = User.objects.create(
            email='manager2@email.com',
            first_name='Manager2',
            last_name='User',
            username='manager2')
        self.manager2.set_password(self.password)
        self.manager2.save()

        ProjectUser.objects.create(
            project=self.fc_project1,
            user=self.manager2,
            role=ProjectUserRoleChoice.objects.get(name='Manager'),
            status=ProjectUserStatusChoice.objects.get(name='Active'))

        assert_has_access(self.manager1, True)
        assert_has_access(self.manager2, True)

    def test_remove_self(self):
        """Test that ProjectRemoveSelf POST performs the correct actions."""
        self.client.login(username=self.user1.username, password=self.password)
        url = reverse(
            'project-remove-self', kwargs={'pk': self.fc_project1.pk})

        pre_time = utc_now_offset_aware()
        response = self.client.post(url, {})

        self.assertRedirects(response, reverse('home'))
        self.assertTrue(ProjectUserRemovalRequest.objects.filter(
            requester=self.user1).exists())

        removal_request = \
            ProjectUserRemovalRequest.objects.filter(requester=self.user1).first()
        self.assertTrue(pre_time <= removal_request.request_time <=
                        utc_now_offset_aware())

        self.client.logout()

    def test_remove_self_superuser(self):
        """Test that ProjectRemoveSelf POST performs the correct actions when
        requester is a superuser."""
        self.user1.is_superuser = True
        self.user1.save()
        self.assertTrue(self.user1.is_superuser)
        self.client.login(username=self.user1.username, password=self.password)

        url = reverse('project-detail', kwargs={'pk': self.fc_project1.pk})
        response = self.client.get(url)
        self.assertContains(response, 'Leave Project')

        url = reverse(
            'project-remove-self', kwargs={'pk': self.fc_project1.pk})
        pre_time = utc_now_offset_aware()
        response = self.client.post(url, {})

        self.assertRedirects(response, reverse('home'))
        self.assertTrue(ProjectUserRemovalRequest.objects.filter(
            requester=self.user1).exists())

        removal_request = \
            ProjectUserRemovalRequest.objects.filter(requester=self.user1).first()
        self.assertTrue(pre_time <= removal_request.request_time <=
                        utc_now_offset_aware())

        self.client.logout()


class TestProjectRemoveUsersView(TestBase):
    """A class for testing ProjectRemoveUsersView."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

    def test_permissions_remove_users_view(self):
        """
        Testing permissions for ProjectRemoveUsersView
        """
        def assert_has_access(user, has_access=True):
            """Assert that the given user has or does not have access to
            the URL. Optionally assert that any messages were sent to
            the user."""
            self.client.login(username=user.username, password=self.password)
            url = reverse(
                'project-remove-users', kwargs={'pk': self.fc_project1.pk})
            status_code = HTTPStatus.OK if has_access else HTTPStatus.FORBIDDEN
            response = self.client.get(url)
            self.assertEqual(response.status_code, status_code)
            self.client.logout()

        # Superusers should have access.
        self.user1.is_superuser = True
        self.user1.save()
        self.assertTrue(self.user1.is_superuser)
        assert_has_access(self.user1, True)

        # normal users should not have access
        assert_has_access(self.user2, False)

        # PIs should have access
        assert_has_access(self.pi1, True)
        assert_has_access(self.pi2, True)

        # manage users should have access
        assert_has_access(self.manager1, True)


class TestProjectRemovalRequestListView(TestBase):
    """A class for testing ProjectRemovalRequestListView."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

    def test_permissions_removal_request_list_view(self):
        """
        Testing permissions for ProjectRemovalRequestListView
        """
        def assert_has_access(user, has_access=True):
            """Assert that the given user has or does not have access to
            the URL. Optionally assert that any messages were sent to
            the user."""
            self.client.login(username=user.username, password=self.password)
            url = reverse(
                'project-removal-request-list')
            status_code = HTTPStatus.OK if has_access else HTTPStatus.FORBIDDEN
            response = self.client.get(url)
            self.assertEqual(response.status_code, status_code)

            self.client.logout()

        # Normal users should not have access
        assert_has_access(self.user1, False)
        assert_has_access(self.user2, False)
        assert_has_access(self.pi1, False)
        assert_has_access(self.pi2, False)
        assert_has_access(self.manager1, False)

        # Superusers should have access.
        self.user1.is_superuser = True
        self.user1.save()
        self.assertTrue(self.user1.is_superuser)
        assert_has_access(self.user1, True)

        # users with permission view_projectuserremovalrequest
        # should have access
        permission = Permission.objects.filter(
            codename='view_projectuserremovalrequest').first()
        self.user2.user_permissions.add(permission)
        self.user2.save()
        self.assertTrue(self.user2.has_perm(
            'project.view_projectuserremovalrequest'))
        assert_has_access(self.user2, True)

    def test_content_removal_request_list_view_pending(self):
        """
        Testing the content rendered on ProjectRemovalRequestListView
        to different users
        """
        completed_removal_request = ProjectUserRemovalRequest.objects.create(
            project_user=self.fc_project1.projectuser_set.get(user=self.manager1),
            requester=self.pi2,
            completion_time=datetime.datetime.now(datetime.timezone.utc),
            status=ProjectUserRemovalRequestStatusChoice.objects.get(
                name='Complete')
        )

        request_runner = ProjectRemovalRequestRunner(
            self.pi1, self.user2, self.fc_project1)
        removal_request = request_runner.run()

        # Superusers should have access.
        self.user1.is_superuser = True
        self.user1.save()
        self.assertTrue(self.user1.is_superuser)

        self.client.login(username=self.user1.username, password=self.password)
        url = reverse(
            'project-removal-request-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, removal_request.project_user.user.username)
        self.assertContains(response, removal_request.requester.username)
        self.assertContains(response, 'Actions')

        self.assertNotContains(response,
                               completed_removal_request.project_user.user.username)
        self.assertNotContains(response,
                               completed_removal_request.requester.username)

        self.client.logout()

        # Staff with permission should have all of the above except
        # actions button
        self.user3 = User.objects.create(
            email='user3@email.com',
            first_name='Normal',
            last_name='User3',
            username='user3')
        self.user3.set_password(self.password)
        self.user3.save()
        permission = Permission.objects.filter(
            codename='view_projectuserremovalrequest').first()
        self.user3.user_permissions.add(permission)
        self.user3.save()
        self.assertTrue(self.user3.has_perm(
            'project.view_projectuserremovalrequest'))

        self.client.login(username=self.user3.username, password=self.password)
        url = reverse(
            'project-removal-request-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, removal_request.project_user.user.username)
        self.assertContains(response, removal_request.requester.username)

        self.assertNotContains(response, 'Actions')
        self.assertNotContains(response,
                               completed_removal_request.project_user.user.username)
        self.assertNotContains(response,
                               completed_removal_request.requester.username)

        self.client.logout()

    def test_content_removal_request_list_view_completed(self):
        """
        Testing the content rendered on ProjectRemovalRequestListView
        to different users
        """
        completed_removal_request = ProjectUserRemovalRequest.objects.create(
            project_user=self.fc_project1.projectuser_set.get(user=self.manager1),
            requester=self.pi2,
            completion_time=datetime.datetime.now(datetime.timezone.utc),
            status=ProjectUserRemovalRequestStatusChoice.objects.get(
                name='Complete')
        )

        request_runner = ProjectRemovalRequestRunner(
            self.pi1, self.user2, self.fc_project1)
        removal_request = request_runner.run()

        # Superusers should have access.
        self.user1.is_superuser = True
        self.user1.save()
        self.assertTrue(self.user1.is_superuser)

        self.client.login(username=self.user1.username, password=self.password)
        url = reverse(
            'project-removal-request-list-completed')
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertNotContains(response,
                               removal_request.project_user.user.username)
        self.assertNotContains(response, removal_request.requester.username)
        self.assertNotContains(response, 'Actions')

        self.assertContains(response,
                            completed_removal_request.project_user.user.username)
        self.assertContains(response,
                            completed_removal_request.requester.username)

        self.client.logout()

        # Staff with permission should see the same page as admins
        self.user3 = User.objects.create(
            email='user3@email.com',
            first_name='Normal',
            last_name='User3',
            username='user3')
        self.user3.set_password(self.password)
        self.user3.save()
        permission = Permission.objects.filter(
            codename='view_projectuserremovalrequest').first()
        self.user3.user_permissions.add(permission)
        self.user3.save()
        self.assertTrue(self.user3.has_perm(
            'project.view_projectuserremovalrequest'))

        self.client.login(username=self.user3.username, password=self.password)
        url = reverse(
            'project-removal-request-list-completed')
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertNotContains(response,
                               removal_request.project_user.user.username)
        self.assertNotContains(response, removal_request.requester.username)
        self.assertNotContains(response, 'Actions')

        self.assertContains(response,
                            completed_removal_request.project_user.user.username)
        self.assertContains(response,
                            completed_removal_request.requester.username)

        self.client.logout()


class TestProjectRemovalRequestUpdateStatusView(TestBase):
    """A class for testing ProjectRemovalRequestUpdateStatusView."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

    def test_permissions_removal_request_update_status_view(self):
        """
        Testing permissions to access ProjectRemovalRequestUpdateStatusView
        """
        def assert_has_access(user, has_access=True):
            """Assert that the given user has or does not have access to
            the URL. Optionally assert that any messages were sent to
            the user."""
            self.client.login(username=user.username, password=self.password)
            url = reverse(
                'project-removal-request-update-status',
                kwargs={'pk': removal_request.pk})
            status_code = HTTPStatus.OK if has_access else HTTPStatus.FORBIDDEN
            response = self.client.get(url)
            self.assertEqual(response.status_code, status_code)

            self.client.logout()

        request_runner = ProjectRemovalRequestRunner(
            self.pi1, self.user2, self.fc_project1)
        removal_request = request_runner.run()

        # Superusers should have access.
        self.user1.is_superuser = True
        self.user1.save()
        self.assertTrue(self.user1.is_superuser)
        assert_has_access(self.user1, True)

        # No other users should have access
        assert_has_access(self.manager1, False)
        assert_has_access(self.pi1, False)
        assert_has_access(self.pi2, False)
        assert_has_access(self.user2, False)

    def test_removal_request_update_status_view(self):
        """
        Testing ProjectRemovalRequestUpdateStatusView POST request
        performs the correct actions
        """
        request_runner = ProjectRemovalRequestRunner(
            self.pi1, self.user2, self.fc_project1)
        removal_request = request_runner.run()

        # Superusers should have access.
        self.user1.is_superuser = True
        self.user1.save()
        self.assertTrue(self.user1.is_superuser)

        self.client.login(username=self.user1.username, password=self.password)
        url = reverse(
            'project-removal-request-update-status',
            kwargs={'pk': removal_request.pk})
        data = {'status': 'Processing'}
        response = self.client.post(url, data)
        self.assertRedirects(response, reverse('project-removal-request-list'))
        removal_request.refresh_from_db()
        self.assertEqual(removal_request.status.name, 'Processing')
        self.client.logout()


class TestProjectRemovalRequestCompleteStatusView(TestBase):
    """A class for testing ProjectRemovalRequestCompleteStatusView."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

        # Create a "Processing" request.
        request_runner = ProjectRemovalRequestRunner(
            self.pi1, self.user2, self.fc_project1)
        self.removal_request = request_runner.run()
        self.removal_request.status = \
            ProjectUserRemovalRequestStatusChoice.objects.get(
                name='Processing')
        self.removal_request.save()

        # Set a superuser.
        self.user1.is_superuser = True
        self.user1.save()

        # Disable notifications for one PI.
        self.fc_project1.projectuser_set.filter(user=self.pi2).update(
            enable_notifications=False)

        self.project_user_obj = ProjectUser.objects.get(
            project=self.fc_project1, user=self.user2)
        self.allocation_user_obj = AllocationUser.objects.get(
            allocation__project=self.project_user_obj.project, user=self.user2)
        self.allocation_user_attribute_obj = \
            self.allocation_user_obj.allocationuserattribute_set.get(
                allocation_attribute_type__name='Cluster Account Status')

    def _assert_emails_sent(self):
        """Assert that emails are sent from the expected sender to the
        expected recipients, with the expected body."""
        expected_from = settings.EMAIL_SENDER
        expected_to = {
            user.email for user in [self.user2, self.pi1, self.manager1]}
        user_name = f'{self.user2.first_name} {self.user2.last_name}'
        pi_name = f'{self.pi1.first_name} {self.pi1.last_name}'
        project_name = self.fc_project1.name
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

    def _assert_message_counts(self, response, num_debug=0, num_info=0,
                               num_success=0, num_warning=0, num_error=0):
        """Assert that the given response has the given number of
        success and warning messages, and that the total number of
        messages is equal to their sum."""
        actual_num_debug = 0
        actual_num_info = 0
        actual_num_success = 0
        actual_num_warning = 0
        actual_num_error = 0

        _messages = get_messages(response.wsgi_request)
        for message in _messages:
            if message.level == messages.DEBUG:
                actual_num_debug += 1
            if message.level == messages.INFO:
                actual_num_info += 1
            elif message.level == messages.SUCCESS:
                actual_num_success += 1
            elif message.level == messages.WARNING:
                actual_num_warning += 1
            elif message.level == messages.ERROR:
                actual_num_error += 1

        self.assertEqual(num_debug, actual_num_debug)
        self.assertEqual(num_info, actual_num_info)
        self.assertEqual(num_success, actual_num_success)
        self.assertEqual(num_warning, actual_num_warning)
        self.assertEqual(num_error, actual_num_error)
        self.assertEqual(
            len(_messages),
            num_debug + num_info + num_success + num_warning + num_error)

    def _assert_post_state(self, pre_time, post_time):
        """Assert that the relevant objects have the expected state,
        assuming that the runner has run successfully. In particular,
        assert that the request's completion_time is between the given
        two times."""
        self._refresh_objects()
        self.assertEqual(self.project_user_obj.status.name, 'Removed')
        self.assertEqual(self.allocation_user_obj.status.name, 'Removed')
        self.assertEqual(self.allocation_user_attribute_obj.value, 'Denied')
        self.assertEqual(self.removal_request.status.name, 'Complete')
        self.assertTrue(
            pre_time <= self.removal_request.completion_time <= post_time)

    def _assert_pre_state(self):
        """Assert that the relevant objects have the expected state,
        assuming that the runner has either not run or not run
        successfully."""
        self._refresh_objects()
        self.assertEqual(self.project_user_obj.status.name, 'Pending - Remove')
        self.assertEqual(self.allocation_user_obj.status.name, 'Active')
        self.assertEqual(self.allocation_user_attribute_obj.value, 'Active')
        self.assertEqual(self.removal_request.status.name, 'Processing')
        self.assertFalse(self.removal_request.completion_time)

    def _refresh_objects(self):
        """Refresh relevant objects from the database."""
        self.project_user_obj.refresh_from_db()
        self.allocation_user_obj.refresh_from_db()
        self.allocation_user_attribute_obj.refresh_from_db()
        self.removal_request.refresh_from_db()

    @staticmethod
    def _get_url(pk):
        """Return the URL for the view for the request with the given
        primary key."""
        return reverse(
            'project-removal-request-complete-status', kwargs={'pk': pk})

    def _post_with_status(self, pk, status_name, assert_success=True):
        """Make a POST request as a superuser to set the status of the
        request with the given primary key to the one with the given
        name. Return the response. Optionally assert that the request
        was successful."""
        self.client.login(username=self.user1.username, password=self.password)
        url = self._get_url(pk)
        data = {'status': status_name}
        response = self.client.post(url, data)
        if assert_success:
            self.assertRedirects(
                response, reverse('project-removal-request-list'))
        return response

    def test_displays_warnings(self):
        """Test that, when warnings are raised during processing, they
        are displayed to the user."""
        self.allocation_user_obj.delete()

        pre_time = utc_now_offset_aware()
        status_name = 'Complete'
        response = self._post_with_status(self.removal_request.pk, status_name)
        post_time = utc_now_offset_aware()

        self.project_user_obj.refresh_from_db()
        self.removal_request.refresh_from_db()
        self.assertEqual(self.project_user_obj.status.name, 'Removed')
        self.assertEqual(self.removal_request.status.name, 'Complete')
        self.assertTrue(
            pre_time <= self.removal_request.completion_time <= post_time)
        self._assert_emails_sent()

        self._assert_message_counts(response, num_success=1, num_warning=1)

    def test_email_failure_not_causes_rollback(self):
        """Test that, when an exception occurs when attempting to send
        an email, changes made so far are not rolled back because such
        an exception is caught."""
        self._assert_pre_state()

        method_to_patch = (
            'coldfront.core.project.utils_.removal_utils.send_email_template')
        with patch(method_to_patch) as send_email_method:
            send_email_method.side_effect = raise_exception
            pre_time = utc_now_offset_aware()
            status_name = 'Complete'
            response = self._post_with_status(
                self.removal_request.pk, status_name)
            post_time = utc_now_offset_aware()

        self._assert_post_state(pre_time, post_time)
        self.assertEqual(len(mail.outbox), 0)
        self._assert_message_counts(response, num_success=1, num_warning=1)

    def test_exception_causes_rollback(self):
        """Test that, when an exception occurs, changes made so far are
        rolled back."""
        self._assert_pre_state()

        with patch.object(
                ProjectRemovalRequestProcessingRunner, 'run', raise_exception):
            status_name = 'Complete'
            response = self._post_with_status(
                self.removal_request.pk, status_name)

        self._assert_pre_state()
        self.assertEqual(len(mail.outbox), 0)
        self._assert_message_counts(response, num_error=1)

    def test_permissions(self):
        """Test that only the expected users have access to the view."""

        def assert_has_access(user, has_access=True):
            """Assert that the given user has or does not have access to
            the URL."""
            self.client.login(username=user.username, password=self.password)
            url = self._get_url(self.removal_request.pk)
            status_code = HTTPStatus.OK if has_access else HTTPStatus.FORBIDDEN
            response = self.client.get(url)
            self.assertEqual(response.status_code, status_code)
            self.client.logout()

        # Superusers should have access.
        self.assertTrue(self.user1.is_superuser)
        assert_has_access(self.user1, True)

        # No other users should have access.
        assert_has_access(self.manager1, False)
        assert_has_access(self.pi1, False)
        assert_has_access(self.pi2, False)
        assert_has_access(self.user2, False)

    def test_removal_request_complete_status_view(self):
        """
        Testing ProjectRemovalRequestCompleteStatusView POST request
        performs the correct actions
        """
        request_runner = ProjectRemovalRequestRunner(
            self.pi1, self.user2, self.fc_project1)
        self.removal_request.refresh_from_db()
        self.removal_request.status = \
            ProjectUserRemovalRequestStatusChoice.objects.get(name='Processing')
        self.removal_request.save()

        # Superusers should have access.
        self.user1.is_superuser = True
        self.user1.save()
        self.assertTrue(self.user1.is_superuser)

        self.client.login(username=self.user1.username, password=self.password)
        url = reverse(
            'project-removal-request-complete-status',
            kwargs={'pk': self.removal_request.pk})
        data = {'status': 'Complete'}

        pre_time = utc_now_offset_aware()
        response = self.client.post(url, data)

        self.assertRedirects(response, reverse('project-removal-request-list'))

        self.removal_request.refresh_from_db()
        self.assertEqual(self.removal_request.status.name, 'Complete')
        self.assertTrue(pre_time <= self.removal_request.completion_time <=
                        utc_now_offset_aware())

        proj_user = self.fc_project1.projectuser_set.get(user=self.user2)
        self.assertEqual(proj_user.status.name, 'Removed')

        allocation_obj = Allocation.objects.get(project=self.fc_project1)
        allocation_user = \
            allocation_obj.allocationuser_set.get(user=self.user2)
        allocation_user_status_choice_removed = \
            AllocationUserStatusChoice.objects.get(name='Removed')

        allocation_user.refresh_from_db()
        self.assertEquals(allocation_user.status,
                          allocation_user_status_choice_removed)

        cluster_account_status = \
            allocation_user.allocationuserattribute_set.get(
                allocation_attribute_type=AllocationAttributeType.objects.get(
                    name='Cluster Account Status'))

        self.assertEquals(cluster_account_status.value, 'Denied')

        self.client.logout()

    def test_emails_removal_request_complete_status_view(self):
        """
        Testing emails sent after admin changes status to Complete in
        ProjectRemovalRequestCompleteStatusView
        """
        pi2_proj_user = self.fc_project1.projectuser_set.get(user=self.pi2)
        pi2_proj_user.enable_notifications = False
        pi2_proj_user.save()

        self.assertFalse(pi2_proj_user.enable_notifications)

        request_runner = ProjectRemovalRequestRunner(
            self.pi1, self.user2, self.fc_project1)
        request_runner.run()
        self.removal_request.status = \
            ProjectUserRemovalRequestStatusChoice.objects.get(name='Processing')
        self.removal_request.save()

        # Superusers should have access.
        self.user1.is_superuser = True
        self.user1.save()
        self.assertTrue(self.user1.is_superuser)

        self.client.login(username=self.user1.username, password=self.password)
        url = reverse(
            'project-removal-request-complete-status',
            kwargs={'pk': self.removal_request.pk})
        data = {'status': 'Complete'}
        response = self.client.post(url, data)
        self.assertRedirects(response, reverse('project-removal-request-list'))

        email_to_list = [proj_user.user.email for proj_user in
                         self.fc_project1.projectuser_set.filter(
                             role__name__in=['Manager', 'Principal Investigator'],
                             status__name='Active',
                             enable_notifications=True)] + [self.user2.email]
        self.assertEqual(len(mail.outbox), len(email_to_list))

        email_body = f'The request to remove {self.user2.first_name} ' \
                     f'{self.user2.last_name} of Project ' \
                     f'{self.fc_project1.name} initiated by {self.pi1.first_name}' \
                     f' {self.pi1.last_name} has been completed. ' \
                     f'{self.user2.first_name} {self.user2.last_name}' \
                     f' is no longer a user of Project {self.fc_project1.name}.'

        for email in mail.outbox:
            self.assertIn(email_body, email.body)
            self.assertIn(email.to[0], email_to_list)
            self.assertNotEqual(email.to[0], self.pi2.email)
            self.assertEqual(settings.EMAIL_SENDER, email.from_email)

        self.client.logout()

        self.removal_request.refresh_from_db()
        self.assertEqual(self.removal_request.status.name, 'Complete')

    def test_success_complete(self):
        """Test that setting the status of the request to 'Complete'
        triggers the expected changes."""
        self.assertEqual(len(mail.outbox), 0)
        self._assert_pre_state()

        pre_time = utc_now_offset_aware()
        status_name = 'Complete'
        response = self._post_with_status(self.removal_request.pk, status_name)
        post_time = utc_now_offset_aware()

        self._assert_post_state(pre_time, post_time)
        self._assert_emails_sent()
        self._assert_message_counts(response, num_success=1)

    def test_success_processing(self):
        """Test that setting the status of the request to 'Processing'
        does not trigger any other changes."""
        self._assert_pre_state()

        status_name = 'Processing'
        response = self._post_with_status(self.removal_request.pk, status_name)

        self._assert_pre_state()
        self.assertEqual(len(mail.outbox), 0)
        self._assert_message_counts(response, num_success=1)

    def test_unexpected_status(self):
        """Test that, when a status other than 'Processing' or
        'Complete' is given, an error message is displayed to the
        user."""
        for status_name in ['Denied', 'Pending', 'Unexpected']:
            response = self._post_with_status(
                self.removal_request.pk, status_name, assert_success=False)
            self.assertContains(response, 'Select a valid choice.')
        self._assert_pre_state()
        self.assertEqual(len(mail.outbox), 0)
