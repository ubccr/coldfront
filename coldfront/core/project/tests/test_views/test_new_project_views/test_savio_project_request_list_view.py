from coldfront.core.project.models import ProjectAllocationRequestStatusChoice
from coldfront.core.project.tests.utils import create_project_and_request
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period
from coldfront.core.utils.tests.test_base import TestBase
from django.contrib.auth.models import User
from django.urls import reverse


class TestViewMixin(object):
    """A mixin for testing SavioProjectRequestListView."""

    completed_url = reverse('new-project-completed-request-list')
    pending_url = reverse('new-project-pending-request-list')
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
        computing_allowance = TestBase.get_fca_computing_allowance()
        allocation_period = get_current_allowance_year_period()
        self.project_a, self.request_a = create_project_and_request(
            'project_a', 'New', computing_allowance, allocation_period,
            self.user_a, self.user_a, 'Under Review')
        self.project_b, self.request_b = create_project_and_request(
            'project_b', 'New', computing_allowance, allocation_period,
            self.user_b, self.user_b, 'Under Review')
        self.project_c, self.request_c = create_project_and_request(
            'project_c', 'New', computing_allowance, allocation_period,
            self.user_c, self.user_c, 'Under Review')

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
        self.assertContains(response, 'Completed New Project Requests')


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
        self.assertContains(response, 'No completed new project requests!')

    def test_type(self):
        """Test that the correct type is displayed on the page."""
        response = self.client.get(self.url)
        self.assertContains(response, 'Pending New Project Requests')
