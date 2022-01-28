from coldfront.core.allocation.models import AllocationAdditionRequest
from coldfront.core.allocation.models import AllocationAdditionRequestStatusChoice
from coldfront.core.utils.tests.test_base import TestBase
from decimal import Decimal
from django.contrib.auth.models import Permission
from django.contrib.auth.models import User
from django.urls import reverse


class TestViewMixin(object):
    """A mixin for testing AllocationAdditionRequestListView."""

    completed_url = reverse('service-units-purchase-completed-request-list')
    pending_url = reverse('service-units-purchase-pending-request-list')
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

        # Create two Projects.
        self.project_a = self.create_active_project_with_pi(
            'ac_project_a', self.user_a)
        self.project_b = self.create_active_project_with_pi(
            'ac_project_b', self.user_b)

        # Create two requests.
        self.request_a = self.create_request(self.project_a, self.user_a)
        self.request_b = self.create_request(self.project_b, self.user_b)

    @staticmethod
    def create_request(project, requester):
        """Create an 'Under Review' request for the given Project by the
        given requester."""
        return AllocationAdditionRequest.objects.create(
            requester=requester,
            project=project,
            status=AllocationAdditionRequestStatusChoice.objects.get(
                name='Under Review'),
            num_service_units=Decimal('1000.00'))

    def test_all_requests_visible_to_superusers(self):
        """Test that superusers can see all requests, even if they are
        not associated with them."""
        self.assertTrue(self.user.is_superuser)
        self.client.login(username=self.user.username, password=self.password)
        response = self.client.get(self.url)
        self.assertContains(response, self.project_a.name)
        self.assertContains(response, self.project_b.name)

    def test_all_requests_visible_to_users_with_permission(self):
        """Test that users who have the appropriate permission can see
        all requests, even if they are not associated with them."""
        self.user.is_superuser = False
        self.user.save()

        # Re-fetch the user to avoid permission caching.
        permission = Permission.objects.get(
            codename='view_allocationadditionrequest')
        self.user.user_permissions.add(permission)
        self.user = User.objects.get(pk=self.user.pk)
        self.assertTrue(
            self.user.has_perm(f'allocation.{permission.codename}'))

        self.client.login(username=self.user.username, password=self.password)
        response = self.client.get(self.url)
        self.assertContains(response, self.project_a.name)
        self.assertContains(response, self.project_b.name)

    def test_requests_visible_to_pis_and_managers(self):
        """Test that PIs and Managers can only see requests associated
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


class TestAllocationAdditionRequestCompletedListView(TestViewMixin, TestBase):
    """A class for testing AllocationAdditionRequestListView for
    completed requests."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.url = self.completed_url
        self.request_a.status = \
            AllocationAdditionRequestStatusChoice.objects.get(name='Complete')
        self.request_a.save()
        self.request_b.status = \
            AllocationAdditionRequestStatusChoice.objects.get(name='Denied')
        self.request_b.save()

    def test_pending_list_empty(self):
        """Test that no requests appear in the pending view, since all
        requests have a completed status."""
        response = self.client.get(self.pending_url)
        self.assertContains(response, 'No pending purchase requests!')

    def test_type(self):
        """Test that the correct type is displayed on the page."""
        response = self.client.get(self.url)
        self.assertContains(
            response, 'Completed Service Units Purchase Requests')


class TestAllocationAdditionRequestPendingListView(TestViewMixin, TestBase):
    """A class for testing AllocationAdditionRequestListView for
    pending requests."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.url = self.pending_url
        pending_status = AllocationAdditionRequestStatusChoice.objects.get(
            name='Under Review')
        AllocationAdditionRequest.objects.update(status=pending_status)

    def test_completed_list_empty(self):
        """Test that no requests appear in the completed view, since all
        requests have a pending status."""
        response = self.client.get(self.completed_url)
        self.assertContains(response, 'No completed purchase requests!')

    def test_type(self):
        """Test that the correct type is displayed on the page."""
        response = self.client.get(self.url)
        self.assertContains(
            response, 'Pending Service Units Purchase Requests')
