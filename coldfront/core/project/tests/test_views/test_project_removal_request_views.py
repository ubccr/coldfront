from django.test import TestCase
from django.contrib.messages import get_messages
from django.urls import reverse
from http import HTTPStatus

from coldfront.core.project.models import *
from coldfront.core.project.utils_.removal_utils import ProjectRemovalRequestRunner
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.user.models import *
from coldfront.core.allocation.models import *
from coldfront.api.statistics.utils import create_project_allocation
from coldfront.api.statistics.utils import create_user_project_allocation

from django.contrib.auth.models import User, Permission
from django.core import mail
from django.core.management import call_command

from io import StringIO
import os
import sys


class TestBase(TestCase):
    """Base class for testing project removal request views"""

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
            'create_staff_group',
            'add_default_user_choices',
        ]
        sys.stdout = open(os.devnull, 'w')
        for command in commands:
            call_command(command, stdout=out, stderr=err)
        sys.stdout = sys.__stdout__

        self.password = 'password'

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
            user=self.manager1,
            role=manager_project_role,
            status=active_project_user_status)

        # add users to project
        for user in [self.user1, self.user2]:
            ProjectUser.objects.create(
                project=self.project1,
                user=user,
                role=user_project_role,
                status=active_project_user_status)

        num_service_units = Decimal('0.00')
        create_project_allocation(self.project1, num_service_units)
        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Cluster Account Status')

        for user in [self.user1, self.user2, self.pi1, self.pi2, self.manager1]:
            objects = create_user_project_allocation(
                user, self.project1, num_service_units)
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

        def get_message_strings(response):
            """Return messages included in the given response as a list of
            strings."""
            return [str(m) for m in get_messages(response.wsgi_request)]

        def assert_has_access(user, has_access=True, expected_messages=[]):
            """Assert that the given user has or does not have access to
            the URL. Optionally assert that any messages were sent to
            the user."""
            self.client.login(username=user.username, password=self.password)
            url = reverse(
                'project-remove-self', kwargs={'pk': self.project1.pk})
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
            project=self.project1,
            user=self.manager2,
            role=ProjectUserRoleChoice.objects.get(name='Manager'),
            status=ProjectUserStatusChoice.objects.get(name='Active'))

        assert_has_access(self.manager1, True)
        assert_has_access(self.manager2, True)

    def test_remove_self(self):
        """Test that ProjectRemoveSelf POST performs the correct actions."""
        self.client.login(username=self.user1.username, password=self.password)
        url = reverse(
            'project-remove-self', kwargs={'pk': self.project1.pk})

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

        url = reverse('project-detail', kwargs={'pk': self.project1.pk})
        response = self.client.get(url)
        self.assertContains(response, 'Leave Project')

        url = reverse(
            'project-remove-self', kwargs={'pk': self.project1.pk})
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
                'project-remove-users', kwargs={'pk': self.project1.pk})
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
            project_user=self.project1.projectuser_set.get(user=self.manager1),
            requester=self.pi2,
            completion_time=datetime.datetime.now(datetime.timezone.utc),
            status=ProjectUserRemovalRequestStatusChoice.objects.get(
                name='Complete')
        )

        request_runner = ProjectRemovalRequestRunner(
            self.pi1, self.user2, self.project1)
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
            project_user=self.project1.projectuser_set.get(user=self.manager1),
            requester=self.pi2,
            completion_time=datetime.datetime.now(datetime.timezone.utc),
            status=ProjectUserRemovalRequestStatusChoice.objects.get(
                name='Complete')
        )

        request_runner = ProjectRemovalRequestRunner(
            self.pi1, self.user2, self.project1)
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
            self.pi1, self.user2, self.project1)
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
            self.pi1, self.user2, self.project1)
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

    def test_permissions_removal_request_complete_status_view(self):
        """
        Testing permissions to access ProjectRemovalRequestCompleteStatusView
        """
        def assert_has_access(user, has_access=True):
            """Assert that the given user has or does not have access to
            the URL. Optionally assert that any messages were sent to
            the user."""
            self.client.login(username=user.username, password=self.password)
            url = reverse(
                'project-removal-request-complete-status',
                kwargs={'pk': removal_request.pk})
            status_code = HTTPStatus.OK if has_access else HTTPStatus.FORBIDDEN
            response = self.client.get(url)
            self.assertEqual(response.status_code, status_code)

            self.client.logout()

        request_runner = ProjectRemovalRequestRunner(
            self.pi1, self.user2, self.project1)
        removal_request = request_runner.run()
        removal_request.status = \
            ProjectUserRemovalRequestStatusChoice.objects.get(name='Processing')
        removal_request.save()

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

    def test_removal_request_complete_status_view(self):
        """
        Testing ProjectRemovalRequestCompleteStatusView POST request
        performs the correct actions
        """
        request_runner = ProjectRemovalRequestRunner(
            self.pi1, self.user2, self.project1)
        removal_request = request_runner.run()
        removal_request.status = \
            ProjectUserRemovalRequestStatusChoice.objects.get(name='Processing')
        removal_request.save()

        # Superusers should have access.
        self.user1.is_superuser = True
        self.user1.save()
        self.assertTrue(self.user1.is_superuser)

        self.client.login(username=self.user1.username, password=self.password)
        url = reverse(
            'project-removal-request-complete-status',
            kwargs={'pk': removal_request.pk})
        data = {'status': 'Complete'}

        pre_time = utc_now_offset_aware()
        response = self.client.post(url, data)

        self.assertRedirects(response, reverse('project-removal-request-list'))

        removal_request.refresh_from_db()
        self.assertEqual(removal_request.status.name, 'Complete')
        self.assertTrue(pre_time <= removal_request.completion_time <=
                        utc_now_offset_aware())

        proj_user = self.project1.projectuser_set.get(user=self.user2)
        self.assertEqual(proj_user.status.name, 'Removed')

        allocation_obj = Allocation.objects.get(project=self.project1)
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
        pi2_proj_user = self.project1.projectuser_set.get(user=self.pi2)
        pi2_proj_user.enable_notifications = False
        pi2_proj_user.save()

        self.assertFalse(pi2_proj_user.enable_notifications)

        request_runner = ProjectRemovalRequestRunner(
            self.pi1, self.user2, self.project1)
        removal_request = request_runner.run()
        removal_request.status = \
            ProjectUserRemovalRequestStatusChoice.objects.get(name='Processing')
        removal_request.save()

        # Superusers should have access.
        self.user1.is_superuser = True
        self.user1.save()
        self.assertTrue(self.user1.is_superuser)

        self.client.login(username=self.user1.username, password=self.password)
        url = reverse(
            'project-removal-request-complete-status',
            kwargs={'pk': removal_request.pk})
        data = {'status': 'Complete'}
        response = self.client.post(url, data)
        self.assertRedirects(response, reverse('project-removal-request-list'))

        email_to_list = [proj_user.user.email for proj_user in
                         self.project1.projectuser_set.filter(
                             role__name__in=['Manager', 'Principal Investigator'],
                             status__name='Active',
                             enable_notifications=True)] + [self.user2.email]
        self.assertEqual(len(mail.outbox), len(email_to_list))

        email_body = f'The request to remove {self.user2.first_name} ' \
                     f'{self.user2.last_name} of Project ' \
                     f'{self.project1.name} initiated by {self.pi1.first_name}' \
                     f' {self.pi1.last_name} has been completed. ' \
                     f'{self.user2.first_name} {self.user2.last_name}' \
                     f' is no longer a user of Project {self.project1.name}.'

        for email in mail.outbox:
            self.assertIn(email_body, email.body)
            self.assertIn(email.to[0], email_to_list)
            self.assertNotEqual(email.to[0], self.pi2.email)
            self.assertEqual(settings.EMAIL_SENDER, email.from_email)

        self.client.logout()

        removal_request.refresh_from_db()
        self.assertEqual(removal_request.status.name, 'Complete')
