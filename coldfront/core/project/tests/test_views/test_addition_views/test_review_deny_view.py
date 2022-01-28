from coldfront.core.allocation.models import AllocationAdditionRequest
from coldfront.core.allocation.models import AllocationAdditionRequestStatusChoice
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import TestBase

from decimal import Decimal
from django.urls import reverse
from http import HTTPStatus
import iso8601


class TestAllocationAdditionReviewDenyView(TestBase):
    """A class for testing AllocationAdditionReviewDenyView."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)

        self.user.is_superuser = True
        self.user.save()

        self.project = self.create_active_project_with_pi(
            'ac_project', self.user)

        self.allocation_addition_request = \
            AllocationAdditionRequest.objects.create(
                requester=self.user,
                project=self.project,
                status=AllocationAdditionRequestStatusChoice.objects.get(
                    name='Under Review'),
                num_service_units=Decimal('1000.00'))

    @staticmethod
    def review_deny_url(pk):
        """Return the URL for the view for denying the
        AllocationAdditionRequest with the given primary key."""
        return reverse(
            'service-units-purchase-request-review-deny', kwargs={'pk': pk})

    def test_permissions_get(self):
        """Test that the correct users have permissions to perform GET
        requests."""
        url = self.review_deny_url(self.allocation_addition_request.pk)

        # Superusers should have access.
        self.assertTrue(self.user.is_superuser)
        self.assert_has_access(url, self.user)

        # Non-superusers should not have access.
        self.user.is_superuser = False
        self.user.save()
        expected_messages = [
            'You do not have permission to view the previous page.',
        ]
        self.assert_has_access(
            url, self.user, has_access=False,
            expected_messages=expected_messages)

    def test_permissions_post(self):
        """Test that the correct users have permissions to perform POST
        requests."""
        url = self.review_deny_url(self.allocation_addition_request.pk)
        data = {}

        # Non-superusers should not have access.
        self.user.is_superuser = False
        self.user.save()
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        message = 'You do not have permission to view the previous page.'
        self.assertEqual(message, self.get_message_strings(response)[0])

        # Superusers should have access.
        self.user.is_superuser = True
        self.user.save()
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_updates_request_state(self):
        """Test that a POST request updates the request's 'state'
        field."""
        url = self.review_deny_url(self.allocation_addition_request.pk)
        data = {
            'justification': (
                'This is a test that a POST request updates the request.'),
        }

        pre_time = utc_now_offset_aware()

        redirect_url = reverse(
            'service-units-purchase-request-detail',
            kwargs={'pk': self.allocation_addition_request.pk})
        response = self.client.post(url, data)
        self.assertRedirects(response, redirect_url)
        message = self.get_message_strings(response)[0]
        self.assertIn('has been denied', message)

        post_time = utc_now_offset_aware()

        self.allocation_addition_request.refresh_from_db()
        other = self.allocation_addition_request.state['other']
        self.assertEqual(other['justification'], data['justification'])
        time = iso8601.parse_date(other['timestamp'])
        self.assertTrue(pre_time <= time <= post_time)

    def test_view_blocked_for_inapplicable_statuses(self):
        """Test that requests that are already 'Complete' or 'Denied'
        cannot be modified via the view."""
        url = self.review_deny_url(self.allocation_addition_request.pk)
        data = {}

        redirect_url = reverse(
            'service-units-purchase-request-detail',
            kwargs={'pk': self.allocation_addition_request.pk})
        for status_name in ('Complete', 'Denied'):
            self.allocation_addition_request.status = \
                AllocationAdditionRequestStatusChoice.objects.get(
                    name=status_name)
            # In the 'Denied' case, the view being redirected to expects
            # certain fields in the 'state' field to be set.
            if status_name == 'Denied':
                self.allocation_addition_request.state['other'] = {
                    'justification': (
                        'This is a test of denying an '
                        'AllocationAdditionRequest.'),
                    'timestamp': utc_now_offset_aware().isoformat(),
                }
            self.allocation_addition_request.save()
            response = self.client.post(url, data)
            self.assertRedirects(response, redirect_url)
            message = f'You cannot review a request with status {status_name}.'
            self.assertEqual(message, self.get_message_strings(response)[0])
