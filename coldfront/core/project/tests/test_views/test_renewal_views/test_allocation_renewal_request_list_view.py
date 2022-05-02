from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.allocation.models import AllocationRenewalRequestStatusChoice
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import TestBase
from django.contrib.auth.models import User
from django.urls import reverse


class TestViewMixin(object):
    """A mixin for testing AllocationRenewalRequestListView."""

    completed_url = reverse('pi-allocation-renewal-completed-request-list')
    pending_url = reverse('pi-allocation-renewal-pending-request-list')
    url = None

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)

        self.user.is_superuser = True
        self.user.save()

        # Create two Users.
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

        # Create two requests.
        self.project_a, self.request_a = self.create_project_and_request(
            'project_a', self.user_a)
        self.project_b, self.request_b = self.create_project_and_request(
            'project_b', self.user_b)

    @staticmethod
    def create_project_and_request(project_name, requester_and_pi):
        """Create an active Project with the given name, add the given
        user to it, and create an AllocationRenewalRequest with 'Under
        Review' status. Return both."""
        active_project_status = ProjectStatusChoice.objects.get(name='Active')
        project = Project.objects.create(
            name=project_name,
            title=project_name,
            status=active_project_status)
        pi_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')
        active_project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')
        ProjectUser.objects.create(
            project=project,
            role=pi_role,
            status=active_project_user_status,
            user=requester_and_pi)
        allocation_period = get_current_allowance_year_period()
        under_review_request_status = \
            AllocationRenewalRequestStatusChoice.objects.get(
                name='Under Review')
        allocation_renewal_request = AllocationRenewalRequest.objects.create(
            requester=requester_and_pi,
            pi=requester_and_pi,
            allocation_period=allocation_period,
            status=under_review_request_status,
            pre_project=project,
            post_project=project,
            request_time=utc_now_offset_aware())
        return project, allocation_renewal_request

    def test_all_requests_visible_to_superusers(self):
        """Test that superusers can see all requests, even if they are
        not associated with them."""
        self.assertTrue(self.user.is_superuser)
        self.client.login(username=self.user.username, password=self.password)
        response = self.client.get(self.url)
        self.assertContains(response, self.project_a.name)
        self.assertContains(response, self.project_b.name)

    def test_requests_visible_to_associated_non_superusers(self):
        """Test that non-superusers can only see requests associated
        with them."""
        self.assertFalse(self.user_a.is_superuser)
        self.client.login(
            username=self.user_a.username, password=self.password)
        response = self.client.get(self.url)
        self.assertContains(response, self.project_a.name)
        self.assertNotContains(response, self.project_b.name)

        self.assertFalse(self.user_b.is_superuser)
        self.client.login(
            username=self.user_b.username, password=self.password)
        response = self.client.get(self.url)
        self.assertNotContains(response, self.project_a.name)
        self.assertContains(response, self.project_b.name)


class TestAllocationRenewalRequestCompletedListView(TestViewMixin, TestBase):
    """A class for testing AllocationRenewalRequestListView for
    completed requests."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.url = self.completed_url
        self.request_a.status = \
            AllocationRenewalRequestStatusChoice.objects.get(name='Approved')
        self.request_a.save()
        self.request_b.status = \
            AllocationRenewalRequestStatusChoice.objects.get(name='Complete')
        self.request_b.save()

    def test_approved_requests_displayed_as_approved_scheduled(self):
        """Test that requests with the 'Approved' status are displayed
        as 'Approved - Scheduled'."""
        response = self.client.get(self.completed_url)
        self.assertContains(response, 'Approved - Scheduled')

    def test_pending_list_empty(self):
        """Test that no requests appear in the pending view, since all
        requests have a completed status."""
        response = self.client.get(self.pending_url)
        self.assertContains(response, 'No pending renewal requests!')

    def test_type(self):
        """Test that the correct type is displayed on the page."""
        response = self.client.get(self.url)
        self.assertContains(response, 'Completed Project Renewal Requests')


class TestAllocationRenewalRequestPendingListView(TestViewMixin, TestBase):
    """A class for testing AllocationRenewalRequestListView for pending
    requests."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.url = self.pending_url
        under_review_status = AllocationRenewalRequestStatusChoice.objects.get(
            name='Under Review')
        AllocationRenewalRequest.objects.update(status=under_review_status)

    def test_completed_list_empty(self):
        """Test that no requests appear in the completed view, since all
        requests have a pending status."""
        response = self.client.get(self.completed_url)
        self.assertContains(response, 'No completed renewal requests!')

    def test_type(self):
        """Test that the correct type is displayed on the page."""
        response = self.client.get(self.url)
        self.assertContains(response, 'Pending Project Renewal Requests')
