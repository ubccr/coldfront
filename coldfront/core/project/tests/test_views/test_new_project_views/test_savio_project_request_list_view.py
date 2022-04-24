from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectAllocationRequestStatusChoice
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import TestBase
from django.contrib.auth.models import User
from django.urls import reverse


class TestViewMixin(object):
    """A mixin for testing SavioProjectRequestListView."""

    completed_url = reverse('savio-project-completed-request-list')
    pending_url = reverse('savio-project-pending-request-list')
    url = None

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)

        self.user.is_superuser = True
        self.user.save()

        # Create three Users.
        self.user_a = User.objects.create(
            email='user_a@email.com',
            first_name='User',
            last_name='A',
            username='user_a')
        self.user_a.set_password(self.password)
        self.user_a.save()
        self.user_b = User.objects.create(
            email='user_b@email.com',
            first_name='User',
            last_name='B',
            username='user_b')
        self.user_b.set_password(self.password)
        self.user_b.save()
        self.user_c = User.objects.create(
            email='user_c@email.com',
            first_name='User',
            last_name='C',
            username='user_c')
        self.user_c.set_password(self.password)
        self.user_c.save()

        # Create three requests.
        self.project_a, self.request_a = self.create_project_and_request(
            'project_a', self.user_a)
        self.project_b, self.request_b = self.create_project_and_request(
            'project_b', self.user_b)
        self.project_c, self.request_c = self.create_project_and_request(
            'project_c', self.user_c)

    @staticmethod
    def create_project_and_request(project_name, requester_and_pi):
        """Create a new Project with the given name, and create a new
        project request with 'Under Review' status. Return both."""
        new_project_status = ProjectStatusChoice.objects.get(name='New')
        project = Project.objects.create(
            name=project_name, title=project_name, status=new_project_status)
        allocation_period = get_current_allowance_year_period()
        under_review_request_status = \
            ProjectAllocationRequestStatusChoice.objects.get(
                name='Under Review')
        new_project_request = SavioProjectAllocationRequest.objects.create(
            requester=requester_and_pi,
            allocation_type=SavioProjectAllocationRequest.FCA,
            allocation_period=allocation_period,
            pi=requester_and_pi,
            project=project,
            pool=False,
            survey_answers={},
            status=under_review_request_status,
            request_time=utc_now_offset_aware())
        return project, new_project_request

    def test_all_requests_visible_to_superusers(self):
        """Test that superusers can see all requests, even if they are
        not associated with them."""
        self.assertTrue(self.user.is_superuser)
        self.client.login(username=self.user.username, password=self.password)
        response = self.client.get(self.url)
        self.assertContains(response, self.project_a.name)
        self.assertContains(response, self.project_b.name)
        self.assertContains(response, self.project_c.name)

    def test_requests_visible_to_associated_non_superusers(self):
        """Test that non-superusers can only see requests associated
        with them."""
        self.assertFalse(self.user_a.is_superuser)
        self.client.login(
            username=self.user_a.username, password=self.password)
        response = self.client.get(self.url)
        self.assertContains(response, self.project_a.name)
        self.assertNotContains(response, self.project_b.name)
        self.assertNotContains(response, self.project_c.name)

        self.assertFalse(self.user_b.is_superuser)
        self.client.login(
            username=self.user_b.username, password=self.password)
        response = self.client.get(self.url)
        self.assertNotContains(response, self.project_a.name)
        self.assertContains(response, self.project_b.name)
        self.assertNotContains(response, self.project_c.name)

        self.assertFalse(self.user_c.is_superuser)
        self.client.login(
            username=self.user_c.username, password=self.password)
        response = self.client.get(self.url)
        self.assertNotContains(response, self.project_a.name)
        self.assertNotContains(response, self.project_b.name)
        self.assertContains(response, self.project_c.name)


class TestSavioProjectRequestCompletedListView(TestViewMixin, TestBase):
    """A class for testing SavioProjectRequestListView for completed
    requests."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.url = self.completed_url
        self.request_a.status = \
            ProjectAllocationRequestStatusChoice.objects.get(
                name='Approved - Complete')
        self.request_a.save()
        self.request_b.status = \
            ProjectAllocationRequestStatusChoice.objects.get(
                name='Approved - Scheduled')
        self.request_b.save()
        self.request_c.status = \
            ProjectAllocationRequestStatusChoice.objects.get(name='Denied')
        self.request_c.save()

    def test_pending_list_empty(self):
        """Test that no requests appear in the pending view, since all
        requests have a completed status."""
        response = self.client.get(self.pending_url)
        self.assertContains(response, 'No pending Savio project requests!')

    def test_type(self):
        """Test that the correct type is displayed on the page."""
        response = self.client.get(self.url)
        self.assertContains(response, 'Completed Savio Project Requests')


class TestSavioProjectRequestPendingListView(TestViewMixin, TestBase):
    """A class for testing SavioProjectRequestListView for pending
    requests."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.url = self.pending_url
        self.request_a.status = \
            ProjectAllocationRequestStatusChoice.objects.get(
                name='Approved - Processing')
        self.request_a.save()
        self.request_b.status = \
            ProjectAllocationRequestStatusChoice.objects.get(
                name='Under Review')
        self.request_b.save()
        self.request_c.status = \
            ProjectAllocationRequestStatusChoice.objects.get(
                name='Under Review')
        self.request_c.save()

    def test_completed_list_empty(self):
        """Test that no requests appear in the completed view, since all
        requests have a pending status."""
        response = self.client.get(self.completed_url)
        self.assertContains(response, 'No completed Savio project requests!')

    def test_type(self):
        """Test that the correct type is displayed on the page."""
        response = self.client.get(self.url)
        self.assertContains(response, 'Pending Savio Project Requests')
