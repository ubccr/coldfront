from http import HTTPStatus

from django.contrib.messages import get_messages
from django.urls import reverse

from coldfront.core.project.forms import ProjectReviewUserJoinForm
from coldfront.core.project.models import *
from coldfront.core.user.models import UserProfile
from django.test import TestCase
from django.contrib.auth.models import User
from django.core import mail
from django.core.management import call_command
from coldfront.core.utils.common import utc_now_offset_aware
from django.conf import settings

from io import StringIO
import os
import sys


class TestBase(TestCase):
    """
    Class for testing project join requests after removing
    all auto approval code
    """

    def setUp(self):
        """Set up test data."""
        out, err = StringIO(), StringIO()
        commands = [
            'add_resource_defaults',
            'add_allocation_defaults',
            'import_field_of_science_data',
            'add_default_project_choices',
            'create_staff_group',
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

        for user in [self.user1, self.pi1, self.pi2]:
            user_profile = UserProfile.objects.get(user=user)
            user_profile.access_agreement_signed_date = utc_now_offset_aware()
            user_profile.save()

        active_project_status = ProjectStatusChoice.objects.get(name='Active')
        active_project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')

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

        # Clear the mail outbox.
        mail.outbox = []

    def get_message_strings(self, response):
        """Return messages included in the given response as a list of
        strings."""
        return [str(m) for m in get_messages(response.wsgi_request)]


class TestProjectJoinView(TestBase):
    """
    Testing class for ProjectJoinView
    """
    def setUp(self):
        """Set up test data."""
        super().setUp()

    def test_project_join_request(self):
        """
        Test that ProjectJoinView successfully creates a ProjectUser and a
        ProjectUserJoinRequest
        """
        url = reverse(
            'project-join', kwargs={'pk': self.project1.pk})
        data = {'reason': 'Testing ProjectJoinView. Testing ProjectJoinView.'}
        self.client.login(username=self.user1.username, password=self.password)
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, HTTPStatus.FOUND)

        proj_user = ProjectUser.objects.filter(user=self.user1,
                                               project=self.project1,
                                               status__name='Pending - Add')
        self.assertTrue(proj_user.exists())
        self.assertTrue(ProjectUserJoinRequest.objects.filter(
            project_user=proj_user.first(),
            reason=data['reason']).exists())

        self.client.logout()

    def test_project_join_request_email(self):
        """
        Test that the correct email is sent to managers and
        PIs after a join request
        """
        url = reverse(
            'project-join', kwargs={'pk': self.project1.pk})
        data = {'reason': 'Testing ProjectJoinView. Testing ProjectJoinView.'}
        self.client.login(username=self.user1.username, password=self.password)
        response = self.client.post(url, data)
        self.client.logout()

        email_to_list = [proj_user.user.email for proj_user in
                         self.project1.projectuser_set.filter(
                             role__name__in=['Manager', 'Principal Investigator'],
                             status__name='Active')]

        email_body = f'User {self.user1.first_name} {self.user1.last_name} ' \
                     f'({self.user1.email}) has requested to join your ' \
                     f'project, {self.project1.name} via MyBRC user portal. ' \
                     f'Please approve/deny this request.'

        for email in mail.outbox:
            self.assertIn(email_body, email.body)
            for recipient in email.to:
                self.assertIn(recipient, email_to_list)
            self.assertEqual(settings.EMAIL_SENDER, email.from_email)


class TestProjectReviewJoinRequestsView(TestBase):
    """
    Testing class for ProjectReviewJoinRequestsView
    """
    def setUp(self):
        """Set up test data."""
        super().setUp()
        url = reverse(
            'project-join', kwargs={'pk': self.project1.pk})
        self.data = {'reason': 'Testing ProjectJoinView. Testing ProjectJoinView.'}
        self.client.login(username=self.user1.username, password=self.password)
        response = self.client.post(url, self.data)
        self.client.logout()

    def test_project_join_request_view_content(self):
        """
        Test that project-review-join-requests displays correct requests
        """
        url = reverse(
            'project-review-join-requests', kwargs={'pk': self.project1.pk})
        self.client.login(username=self.pi1.username, password=self.password)
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, self.user1.username)
        self.assertContains(response, self.data['reason'])

    def test_project_join_request_view_approve(self):
        """
        Test project-review-join-requests approval
        """
        proj_user = ProjectUser.objects.filter(user=self.user1,
                                               project=self.project1).first()

        self.assertEqual(proj_user.status.name, 'Pending - Add')

        form_data = {'userform-TOTAL_FORMS': ['1'],
                     'userform-INITIAL_FORMS': ['1'],
                     'userform-MIN_NUM_FORMS': ['0'],
                     'userform-MAX_NUM_FORMS': ['1'],
                     'userform-0-selected': ['on'],
                     'decision': ['approve']}

        url = reverse(
            'project-review-join-requests', kwargs={'pk': self.project1.pk})
        self.client.login(username=self.pi1.username, password=self.password)
        response = self.client.post(url, form_data)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

        proj_user.refresh_from_db()
        self.assertEqual(proj_user.status.name, 'Active')

    def test_project_join_request_view_deny(self):
        """
        Test project-review-join-requests approval
        """
        proj_user = ProjectUser.objects.filter(user=self.user1,
                                               project=self.project1).first()

        self.assertEqual(proj_user.status.name, 'Pending - Add')

        form_data = {'userform-TOTAL_FORMS': ['1'],
                     'userform-INITIAL_FORMS': ['1'],
                     'userform-MIN_NUM_FORMS': ['0'],
                     'userform-MAX_NUM_FORMS': ['1'],
                     'userform-0-selected': ['on'],
                     'decision': ['deny']}

        url = reverse(
            'project-review-join-requests', kwargs={'pk': self.project1.pk})
        self.client.login(username=self.pi1.username, password=self.password)
        response = self.client.post(url, form_data)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

        proj_user.refresh_from_db()
        self.assertEqual(proj_user.status.name, 'Denied')


class TestProjectUpdateView(TestBase):
    """
    Testing class for ProjectUpdateView
    """
    def setUp(self):
        """Set up test data."""
        super().setUp()

    def test_project_update(self):
        """
        Testing ProjectUpdateView functionality after removing auto approvals
        """
        form_data = {'title': 'New Updated Title',
                     'description': 'New Updated Description'}
        url = reverse(
            'project-update', kwargs={'pk': self.project1.pk})
        self.client.login(username=self.pi1.username, password=self.password)
        response = self.client.post(url, form_data)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

        self.assertRedirects(response, reverse('project-detail',
                                               kwargs={'pk': self.project1.pk}))
        self.project1.refresh_from_db()
        self.assertEqual(self.project1.title, form_data['title'])
        self.assertEqual(self.project1.description, form_data['description'])

