from django.urls import reverse
from http import HTTPStatus

from coldfront.core.project.models import *
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import TestBase
from coldfront.core.user.models import *
from coldfront.core.allocation.models import *

from django.contrib.auth.models import User
from django.core import mail

import pytz


class TestProjectJoinRequestListView(TestBase):
    """A class for testing ProjectJoinRequestListView."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

        # Create a normal users
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

        active_project_status = ProjectStatusChoice.objects.get(name='Active')
        self.active_project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')
        self.pending_add = ProjectUserStatusChoice.objects.get(
            name='Pending - Add')

        user_project_role = ProjectUserRoleChoice.objects.get(
            name='User')

        # Create Projects.
        self.project1 = Project.objects.create(
            name='project1', status=active_project_status)

        self.project2 = Project.objects.create(
            name='project2', status=active_project_status)

        # add user1 and user2 with Pending - Add status
        self.project1_user1 = ProjectUser.objects.create(
            user=self.user1,
            project=self.project1,
            role=user_project_role,
            status=self.active_project_user_status)

        self.project1_user2 = ProjectUser.objects.create(
            user=self.user2,
            project=self.project1,
            role=user_project_role,
            status=self.active_project_user_status)

        self.project2_user1 = ProjectUser.objects.create(
            user=self.user1,
            project=self.project2,
            role=user_project_role,
            status=self.active_project_user_status)

        self.project2_user2 = ProjectUser.objects.create(
            user=self.user2,
            project=self.project2,
            role=user_project_role,
            status=self.active_project_user_status)

        # create admin and staff users
        self.admin = User.objects.create(
            email='admin@email.com',
            first_name='admin',
            last_name='admin',
            username='admin')
        self.admin.is_superuser = True
        self.admin.save()

        self.staff = User.objects.create(
            email='staff@email.com',
            first_name='staff',
            last_name='staff',
            username='staff')
        self.staff.is_staff = True
        self.staff.save()

        self.password = 'password'

        for user in [self.user1, self.user2, self.admin, self.staff]:
            user_profile = UserProfile.objects.get(user=user)
            user_profile.access_agreement_signed_date = utc_now_offset_aware()
            user_profile.save()

            user.set_password(self.password)
            user.save()

        # Clear the mail outbox.
        mail.outbox = []

    def assert_has_access(self, user, has_access):
        self.client.login(username=user.username, password=self.password)
        url = reverse('project-join-request-list')
        response = self.client.get(url)
        status_code = HTTPStatus.OK if has_access else HTTPStatus.FORBIDDEN
        self.assertEqual(response.status_code, status_code)
        self.client.logout()

    def get_response(self, user):
        self.client.login(username=user.username, password=self.password)
        url = reverse('project-join-request-list')
        return self.client.get(url)

    def assert_request_shown(self, response, request):
        self.assertContains(response, request.reason)
        request_date = request.created.astimezone(
            pytz.timezone('America/Los_Angeles')).strftime('%b. %d, %Y')
        self.assertContains(response, request_date)
        self.assertContains(response, request.project_user.user.username)
        self.assertContains(response, request.project_user.user.email)
        self.assertContains(response, request.project_user.project.name)

    def test_access(self):
        """
        testing user access to ProjectJoinRequestListView
        """
        # admin and staff should have access
        self.assert_has_access(self.admin, True)
        self.assert_has_access(self.staff, True)

        # normal users should not have access
        self.assert_has_access(self.user1, False)
        self.assert_has_access(self.user2, False)

    def test_no_requests(self):
        """
        ProjectJoinRequestListView with no requests
        """
        response = self.get_response(self.admin)
        self.assertContains(response, 'No pending project join requests!')

    def test_only_old_requests(self):
        """
        ProjectJoinRequestListView with old requests, should not show any requests
        """

        # old requests exist but the project_user status = Active
        request1 = \
            ProjectUserJoinRequest.objects.create(project_user=self.project1_user1,
                                                  reason='test reason 1')

        request2 = \
            ProjectUserJoinRequest.objects.create(project_user=self.project1_user2,
                                                  reason='test reason 2')

        self.assertEqual(self.project1_user1.status.name, 'Active')
        self.assertEqual(self.project1_user2.status.name, 'Active')

        response = self.get_response(self.admin)
        self.assertContains(response, 'No pending project join requests!')
        self.assertNotContains(response, request1.reason)
        self.assertNotContains(response, request2.reason)

    def test_single_request(self):
        """
        ProjectJoinRequestListView with a single pending request
        """
        request1 = \
            ProjectUserJoinRequest.objects.create(project_user=self.project1_user1,
                                                  reason='test reason 1')
        self.project1_user1.status = self.pending_add
        self.project1_user1.save()

        self.assertEqual(self.project1_user1.status.name, 'Pending - Add')

        response = self.get_response(self.admin)
        self.assert_request_shown(response, request1)

    def test_single_request_given_old_requests(self):
        """
        ProjectJoinRequestListView where a user has a pending request
        and multiple old requests
        """
        request1 = \
            ProjectUserJoinRequest.objects.create(project_user=self.project1_user1,
                                                  reason='old request 1')
        request2 = \
            ProjectUserJoinRequest.objects.create(project_user=self.project1_user1,
                                                  reason='old request 2')
        request3 = \
            ProjectUserJoinRequest.objects.create(project_user=self.project1_user1,
                                                  reason='new request 1')
        self.project1_user1.status = self.pending_add
        self.project1_user1.save()

        self.assertEqual(self.project1_user1.status.name, 'Pending - Add')

        response = self.get_response(self.admin)
        self.assertNotContains(response, request1.reason)
        self.assertNotContains(response, request2.reason)
        self.assert_request_shown(response, request3)

    def test_multiple_requests(self):
        """
        ProjectJoinRequestListView with multiple requests from multiple users
        """

        request1 = \
            ProjectUserJoinRequest.objects.create(project_user=self.project1_user1,
                                                  reason='old request 1')
        request2 = \
            ProjectUserJoinRequest.objects.create(project_user=self.project1_user1,
                                                  reason='new request 1')
        request3 = \
            ProjectUserJoinRequest.objects.create(project_user=self.project2_user2,
                                                  reason='new request 2')
        self.project1_user1.status = self.pending_add
        self.project1_user1.save()

        self.project2_user2.status = self.pending_add
        self.project2_user2.save()

        self.assertEqual(self.project1_user1.status.name, 'Pending - Add')
        self.assertEqual(self.project2_user2.status.name, 'Pending - Add')

        response = self.get_response(self.admin)
        self.assertNotContains(response, request1.reason)
        self.assert_request_shown(response, request2)
        self.assert_request_shown(response, request3)