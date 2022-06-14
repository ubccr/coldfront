from copy import deepcopy
from http import HTTPStatus

from django.contrib.auth.models import User

from coldfront.core.project.models import Project, ProjectUser, \
    ProjectUserRoleChoice, ProjectUserStatusChoice, ProjectUserJoinRequest
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.user.models import UserProfile
from coldfront.core.utils.tests.test_base import TestBase

from django.contrib.auth.models import User
from django.conf import settings
from django.test import override_settings
from django.urls import reverse


class TestProjectReviewJoinRequestsView(TestBase):
    """A class for testing ProjectReviewJoinRequestsView."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)

        # Create a PI.
        self.pi = User.objects.create(
            username='pi0', email='pi0@lbl.gov')
        self.pi.set_password(self.password)
        self.pi.save()
        user_profile = UserProfile.objects.get(user=self.pi)
        user_profile.is_pi = True
        user_profile.save()

        self.project0 = self.create_active_project_with_pi('project0', self.pi)
        self.project1 = self.create_active_project_with_pi('project1', self.pi)

    def create_join_request(self, user, project, host_user=None):
        """Creates a join request for a certain project. Returns the response"""

        url = reverse('project-join', kwargs={'pk': project.pk})
        data = {
            'reason': 'This is a test reason for joining the project '
                      'with a host.',
            'host_user': host_user.username if host_user else ''
        }
        self.client.login(username=user.username, password=self.password)
        response = self.client.post(url, data)

        return response

    def test_host_user_submitted_lrc(self):
        """Tests that the host user column is displayed by
        ProjectReviewJoinRequestsView when LRC_ONLY is True."""

        # Setting LRC_ONLY to True and BRC_ONLY to False
        flags_copy = deepcopy(settings.FLAGS)
        flags_copy['LRC_ONLY'] = [{'condition': 'boolean', 'value': True}]
        flags_copy['BRC_ONLY'] = [{'condition': 'boolean', 'value': False}]
        with override_settings(FLAGS=flags_copy):

            # Make a join request with a host user specified and test
            # that it was successfully created.
            response = self.create_join_request(self.user,
                                                self.project0,
                                                host_user=self.pi)
            self.assertEqual(response.status_code, HTTPStatus.FOUND)
            join_request = \
                ProjectUserJoinRequest.objects.get(
                    project_user__user=self.user,
                    project_user__project=self.project0)
            self.assertEqual(join_request.host_user, self.pi)

            # Test that the correct host information is shown.
            self.client.login(username=self.pi.username,
                              password=self.password)
            url = reverse('project-review-join-requests',
                          kwargs={'pk': self.project0.pk})
            response = self.client.get(url)
            self.assertEqual(response.status_code, HTTPStatus.OK)

            html = response.content.decode('utf-8')
            self.assertIn('<th scope="col">Need Host</th>', html)
            self.assertIn('<td>Yes (pi0)</td>', html)

    def test_no_host_user_submitted_lrc(self):
        """Tests that the host user column is displayed by
        ProjectReviewJoinRequestsView when LRC_ONLY is True."""

        # Setting LRC_ONLY to True and BRC_ONLY to False
        flags_copy = deepcopy(settings.FLAGS)
        flags_copy['LRC_ONLY'] = [{'condition': 'boolean', 'value': True}]
        flags_copy['BRC_ONLY'] = [{'condition': 'boolean', 'value': False}]
        with override_settings(FLAGS=flags_copy):

            # Make a join request without a host user specified and test
            # that it was successfully created.
            response = self.create_join_request(self.user,
                                                self.project0)
            self.assertEqual(response.status_code, HTTPStatus.FOUND)
            join_request = \
                ProjectUserJoinRequest.objects.get(
                    project_user__user=self.user,
                    project_user__project=self.project0)
            self.assertEqual(join_request.host_user, None)

            # Test that the correct host information is shown.
            self.client.login(username=self.pi.username,
                              password=self.password)
            url = reverse('project-review-join-requests',
                          kwargs={'pk': self.project0.pk})
            response = self.client.get(url)
            self.assertEqual(response.status_code, HTTPStatus.OK)

            html = response.content.decode('utf-8')
            self.assertIn('<th scope="col">Need Host</th>', html)
            self.assertIn('<td>No</td>', html)

    def test_host_user_brc(self):
        """Test that the host user column is not shown by
        ProjectReviewJoinRequestsView when BRC_ONLY is set to True."""

        # Setting LRC_ONLY to False and BRC_ONLY to True
        flags_copy = deepcopy(settings.FLAGS)
        flags_copy['LRC_ONLY'] = [{'condition': 'boolean', 'value': False}]
        flags_copy['BRC_ONLY'] = [{'condition': 'boolean', 'value': True}]
        with override_settings(FLAGS=flags_copy):

            # Make a join request without a host user specified
            self.create_join_request(self.user, self.project0)

            # Test that the correct host information is shown.
            self.client.login(username=self.pi.username,
                              password=self.password)
            url = reverse('project-review-join-requests',
                          kwargs={'pk': self.project0.pk})
            response = self.client.get(url)
            self.assertEqual(response.status_code, HTTPStatus.OK)

            html = response.content.decode('utf-8')
            self.assertNotIn('<th scope="col">Need Host</th>', html)

    def test_host_user_set(self):
        """Test that ProjectReviewJoinRequestsView correctly sets the host
        user in a user's UserProfile."""

        # Setting LRC_ONLY to True and BRC_ONLY to False
        flags_copy = deepcopy(settings.FLAGS)
        flags_copy['LRC_ONLY'] = [{'condition': 'boolean', 'value': True}]
        flags_copy['BRC_ONLY'] = [{'condition': 'boolean', 'value': False}]
        with override_settings(FLAGS=flags_copy):

            # Make a join request with a host user specified
            self.create_join_request(self.user, self.project0, host_user=self.pi)

            data = {
                'decision': ['approve'],
                'userform-0-selected': ['on'],
                'userform-TOTAL_FORMS': ['1'],
                'userform-INITIAL_FORMS': ['1'],
                'userform-MIN_NUM_FORMS': ['0'],
                'userform-MAX_NUM_FORMS': ['1']
            }

            self.client.login(username=self.pi, password=self.password)
            url = reverse('project-review-join-requests',
                          kwargs={'pk': self.project0.pk})
            response = self.client.post(url, data)
            self.assertEqual(response.status_code, HTTPStatus.FOUND)

            project_user = ProjectUser.objects.get(user=self.user,
                                                   project=self.project0)
            user_profile = UserProfile.objects.get(user=self.user)

            # Test that request is correctly processed.
            self.assertEqual(project_user.status.name, 'Active')
            self.assertEqual(user_profile.host_user, self.pi)
