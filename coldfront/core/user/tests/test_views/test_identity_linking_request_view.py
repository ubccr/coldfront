from coldfront.core.user.models import IdentityLinkingRequest
from coldfront.core.user.models import IdentityLinkingRequestStatusChoice
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import TestBase
from django.contrib.messages import get_messages
from django.test import Client
from django.urls import reverse
from http import HTTPStatus


class TestIdentityLinkingRequestView(TestBase):
    """A class for testing IdentityLinkingRequestView."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.client.login(username=self.user.username, password=self.password)

    @staticmethod
    def get_message_strings(response):
        """Return messages included in the given response as a list of
        strings."""
        return [str(m) for m in get_messages(response.wsgi_request)]

    @staticmethod
    def identity_linking_request_url():
        """Return the URL for requesting a new identity-linking
        email."""
        return reverse('identity-linking-request')

    def test_get_not_allowed(self):
        """Test that GET requests are not allowed."""
        url = self.identity_linking_request_url()
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_login_required(self):
        """Test that unauthenticated users are redirected to the login
        view."""
        self.client = Client()
        url = self.identity_linking_request_url()
        response = self.client.get(url)
        self.assertRedirects(response, reverse('login') + f'?next={url}')

    def test_post_creates_request(self):
        """Test that a POST request creates a pending
        IdentityLinkingRequest."""
        self.assertEqual(IdentityLinkingRequest.objects.count(), 0)
        pre_time = utc_now_offset_aware()

        url = self.identity_linking_request_url()
        response = self.client.post(url)
        self.assertRedirects(response, reverse('user-profile'))
        expected_message = (
            f'A request has been generated. An email will be sent to '
            f'{self.user.email} shortly.')
        actual_messages = self.get_message_strings(response)
        self.assertEqual(expected_message, actual_messages[0])

        post_time = utc_now_offset_aware()
        self.assertEqual(IdentityLinkingRequest.objects.count(), 1)
        identity_linking_request = IdentityLinkingRequest.objects.first()
        self.assertEqual(identity_linking_request.requester, self.user)
        self.assertTrue(
            pre_time <= identity_linking_request.request_time <= post_time)
        self.assertIsNone(identity_linking_request.completion_time)
        self.assertEqual(identity_linking_request.status.name, 'Pending')

    def test_post_disallowed_if_pending_request_exists(self):
        """Test that, if the requesting user already has a pending
        request, an error is raised during a POST request."""
        pending_status = IdentityLinkingRequestStatusChoice.objects.get(
            name='Pending')
        IdentityLinkingRequest.objects.create(
            requester=self.user,
            status=pending_status,
            request_time=utc_now_offset_aware())

        url = self.identity_linking_request_url()
        response = self.client.post(url)
        self.assertRedirects(response, reverse('user-profile'))
        expected_message = (
            'You have already requested a linking email. Please wait until it '
            'has been sent to request another.')
        actual_messages = self.get_message_strings(response)
        self.assertEqual(expected_message, actual_messages[0])
