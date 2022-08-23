from http import HTTPStatus

from django.contrib.auth.models import User
from django.conf import settings
from django.urls import reverse

from coldfront.api.statistics.utils import create_project_allocation
from coldfront.core.allocation.models import AllocationAttribute
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.billing.models import BillingActivity
from coldfront.core.billing.models import BillingProject
from coldfront.core.project.models import ProjectUser, ProjectUserJoinRequest
from coldfront.core.user.models import UserProfile
from coldfront.core.utils.tests.test_base import enable_deployment
from coldfront.core.utils.tests.test_base import TestBase


class TestViewMixin(object):
    """A mixin for testing view functionality common to both
    deployments."""

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

        self.project0 = self.create_active_project_with_pi(
            'fc_project0', self.pi)
        self.allocation0 = create_project_allocation(
            self.project0, settings.ALLOCATION_MIN).allocation

        self.host_user_column_html = '<th scope="col">Need Host</th>'

    def create_join_request(self, user, project, host_user=None):
        """Create a join request for a certain project. Return the
        response."""
        url = reverse('project-join', kwargs={'pk': project.pk})
        data = {
            'reason': (
                'This is a test reason for joining the project with a host.'),
            'host_user': host_user.username if host_user else '',
        }
        self.client.login(username=user.username, password=self.password)
        response = self.client.post(url, data)
        return response

    @staticmethod
    def review_requests_url(project):
        """Return the URL for the view for reviewing join requests to
        the given Project."""
        return reverse(
            'project-review-join-requests', kwargs={'pk': project.pk})


class TestBRCProjectReviewJoinRequestsView(TestViewMixin, TestBase):
    """A class for testing ProjectReviewJoinRequestsView on the BRC
    deployment."""

    @enable_deployment('BRC')
    def setUp(self):
        """Set up test data."""
        super().setUp()

    @enable_deployment('BRC')
    def test_host_user_column_excluded(self):
        """Test that the host user column is excluded."""
        # Make a join request without a host user specified.
        self.create_join_request(self.user, self.project0)

        # Test that the correct host information is shown.
        self.client.login(username=self.pi.username, password=self.password)
        url = self.review_requests_url(self.project0)
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.assertNotContains(response, self.host_user_column_html)

    @enable_deployment('BRC')
    def test_not_sets_user_profile_fields(self):
        """Test that the view does not set the host user and billing
        activity in the requesting User's UserProfile."""
        user_profile = UserProfile.objects.get(user=self.user)
        self.assertIsNone(user_profile.host_user)
        self.assertIsNone(user_profile.billing_activity)

        # Make a join request with a host user specified.
        self.create_join_request(self.user, self.project0, host_user=self.pi)

        project_user = ProjectUser.objects.get(
            user=self.user, project=self.project0)
        self.assertEqual(project_user.status.name, 'Pending - Add')

        data = {
            'decision': ['approve'],
            'userform-0-selected': ['on'],
            'userform-TOTAL_FORMS': ['1'],
            'userform-INITIAL_FORMS': ['1'],
            'userform-MIN_NUM_FORMS': ['0'],
            'userform-MAX_NUM_FORMS': ['1']
        }

        self.client.login(username=self.pi, password=self.password)
        url = self.review_requests_url(self.project0)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

        # The ProjectUser should have the 'Active' status.
        project_user.refresh_from_db()
        self.assertEqual(project_user.status.name, 'Active')

        # The UserProfile should still not have a host_user or a
        # billing_activity.
        user_profile.refresh_from_db()
        self.assertIsNone(user_profile.host_user)
        self.assertIsNone(user_profile.billing_activity)


class TestLRCProjectReviewJoinRequestsView(TestViewMixin, TestBase):
    """A class for testing ProjectReviewJoinRequestsView on the LRC
    deployment."""

    @enable_deployment('LRC')
    def setUp(self):
        """Set up test data."""
        super().setUp()

        # Rename the Projects.
        self.project0.name = 'pc_project0'
        self.project0.save()

        # Set a billing ID for the Project.
        billing_project0 = BillingProject.objects.create(identifier='123456')
        self.billing_activity0 = BillingActivity.objects.create(
            billing_project=billing_project0, identifier='789')
        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Billing Activity')
        self.billing_attribute = AllocationAttribute.objects.create(
            allocation_attribute_type=allocation_attribute_type,
            allocation=self.allocation0,
            value=str(self.billing_activity0.pk))

    @enable_deployment('LRC')
    def test_host_user_submitted(self):
        """Test that the host user column correctly displays that a host
        user was specified in the request."""
        # Make a join request with a host user specified and test that it was
        # successfully created.
        response = self.create_join_request(
            self.user, self.project0, host_user=self.pi)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        join_request = ProjectUserJoinRequest.objects.get(
            project_user__user=self.user,
            project_user__project=self.project0)
        self.assertEqual(join_request.host_user, self.pi)

        # Test that the correct host information is shown.
        self.client.login(username=self.pi.username, password=self.password)
        url = self.review_requests_url(self.project0)
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.assertContains(response, self.host_user_column_html)
        self.assertContains(response, '<td>Yes (pi0)</td>')

    @enable_deployment('LRC')
    def test_no_host_user_submitted(self):
        """Test that the host user column correctly displays that no
        host user was specified in the request."""
        # Make a join request without a host user specified and test that it
        # was successfully created.
        response = self.create_join_request(self.user, self.project0)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        join_request = ProjectUserJoinRequest.objects.get(
            project_user__user=self.user,
            project_user__project=self.project0)
        self.assertEqual(join_request.host_user, None)

        # Test that the correct host information is shown.
        self.client.login(username=self.pi.username, password=self.password)
        url = self.review_requests_url(self.project0)
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.assertContains(response, self.host_user_column_html)
        self.assertContains(response, '<td>No</td>')

    @enable_deployment('LRC')
    def test_post_disallowed_if_project_missing_billing_activity(self):
        """Test that, if the Project does not have a default billing ID,
        POST requests are disallowed."""

        def assert_post_disallowed():
            """Assert that a POST request is disallowed."""
            self.client.login(username=self.pi, password=self.password)
            url = self.review_requests_url(self.project0)
            response = self.client.post(url, {})
            self.assertEqual(response.status_code, HTTPStatus.FOUND)
            # An error message should be propagated to the user.
            messages = self.get_message_strings(response)
            self.assertGreater(len(messages), 0)
            message = messages[-1]
            self.assertIn('does not have a LBL Project ID', message)
            self.assertIn('cannot review', message)
            # The ProjectUser should not have been updated.
            project_user = ProjectUser.objects.get(
                project=self.project0, user=self.user)
            self.assertEqual(project_user.status.name, 'Pending - Add')

        # Make a join request with a host user specified.
        self.create_join_request(self.user, self.project0, host_user=self.pi)

        # Set the Attribute to store an invalid BillingActivity primary key.
        self.billing_attribute.value = str(BillingActivity.objects.count() + 1)
        self.billing_attribute.save()

        assert_post_disallowed()

        # Set the Attribute to store an empty value.
        self.billing_attribute.value = '    '
        self.billing_attribute.save()

        assert_post_disallowed()

        # Delete the Attribute.
        self.billing_attribute.delete()

        assert_post_disallowed()

    @enable_deployment('LRC')
    def test_sets_user_profile_fields(self):
        """Test that the view sets the host user and billing activity in
        the requesting User's UserProfile."""
        user_profile = UserProfile.objects.get(user=self.user)
        self.assertIsNone(user_profile.host_user)
        self.assertIsNone(user_profile.billing_activity)

        # Make a join request with a host user specified.
        self.create_join_request(self.user, self.project0, host_user=self.pi)

        project_user = ProjectUser.objects.get(
            user=self.user, project=self.project0)
        self.assertEqual(project_user.status.name, 'Pending - Add')

        data = {
            'decision': ['approve'],
            'userform-0-selected': ['on'],
            'userform-TOTAL_FORMS': ['1'],
            'userform-INITIAL_FORMS': ['1'],
            'userform-MIN_NUM_FORMS': ['0'],
            'userform-MAX_NUM_FORMS': ['1']
        }

        self.client.login(username=self.pi, password=self.password)
        url = self.review_requests_url(self.project0)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

        # The ProjectUser should have the 'Active' status.
        project_user.refresh_from_db()
        self.assertEqual(project_user.status.name, 'Active')

        # The UserProfile should have both a host_user and a billing_activity.
        user_profile.refresh_from_db()
        self.assertEqual(user_profile.host_user, self.pi)
        self.assertEqual(user_profile.billing_activity, self.billing_activity0)
