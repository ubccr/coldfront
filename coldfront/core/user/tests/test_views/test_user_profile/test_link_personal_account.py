from bs4 import BeautifulSoup
from coldfront.core.user.models import IdentityLinkingRequest
from coldfront.core.user.models import IdentityLinkingRequestStatusChoice
from coldfront.core.user.tests.utils import grant_user_cluster_access_under_test_project
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import TestBase
from datetime import timedelta
from django.conf import settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.formats import localize
import pytz


class TestLinkPersonalAccount(TestBase):
    """A class for testing the "Link Your Personal Account" section of
    the User Profile."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.client.login(username=self.user.username, password=self.password)

    @staticmethod
    def user_profile_url():
        """Return the URL to the User Profile."""
        return reverse('user-profile')

    def test_latest_request_conditionally_displayed(self):
        """Test that the sub-section related to the user's latest
        request is only displayed if one exists."""

        def assert_section_displayed(displayed):
            """Assert that the relevant text and headers appear if the
            given boolean is True; otherwise, assert that they do not
            appear."""
            url = self.user_profile_url()
            response = self.client.get(url)
            html = response.content.decode('utf-8')
            func = self.assertIn if displayed else self.assertNotIn
            func('Below is your latest request.', html)
            func('Time Requested', html)
            func('Time Sent', html)

        # No requests exist.
        assert_section_displayed(False)

        # Exactly one pending request exists.
        pending_status = IdentityLinkingRequestStatusChoice.objects.get(
            name='Pending')
        identity_linking_request = IdentityLinkingRequest.objects.create(
            requester=self.user,
            request_time=utc_now_offset_aware(),
            status=pending_status)
        assert_section_displayed(True)

        # Exactly one complete request exists.
        complete_status = IdentityLinkingRequestStatusChoice.objects.get(
            name='Complete')
        identity_linking_request.status = complete_status
        identity_linking_request.save()
        assert_section_displayed(True)

    def test_other_user_requests_not_displayed(self):
        """Test that only requests belonging to the logged in user are
        displayed."""
        requester = User.objects.create(
            email='other_user@email.com',
            first_name='Other',
            last_name='User',
            username='other_user')
        pending_status = IdentityLinkingRequestStatusChoice.objects.get(
            name='Pending')
        IdentityLinkingRequest.objects.create(
            requester=requester,
            request_time=utc_now_offset_aware(),
            status=pending_status)

        url = self.user_profile_url()
        response = self.client.get(url)
        html = response.content.decode('utf-8')
        self.assertNotIn('Below is your latest request.', html)
        self.assertNotIn('Time Requested', html)
        self.assertNotIn('Time Sent', html)

    def test_request_button_conditionally_disabled(self):
        """Test that, if the User (a) does not have active cluster
        access, or (b) has a pending IdentityLinkingRequest, the button
        to request a new one is disabled."""

        def get_button_html():
            """Return the HTML of the request button."""
            url = self.user_profile_url()
            response = self.client.get(url)
            html = response.content.decode('utf-8')
            soup = BeautifulSoup(html, 'html.parser')
            button = soup.find('a', {'id': 'request-linking-email-button'})
            return str(button)

        # The user has cluster access.
        allocation_user_attribute = \
            grant_user_cluster_access_under_test_project(self.user)

        # No requests exist.
        self.assertNotIn('disabled', get_button_html())

        # Exactly one pending request exists.
        pending_status = IdentityLinkingRequestStatusChoice.objects.get(
            name='Pending')
        identity_linking_request = IdentityLinkingRequest.objects.create(
            requester=self.user,
            request_time=utc_now_offset_aware(),
            status=pending_status)
        self.assertIn('disabled', get_button_html())

        # Exactly one complete request exists.
        complete_status = IdentityLinkingRequestStatusChoice.objects.get(
            name='Complete')
        identity_linking_request.status = complete_status
        identity_linking_request.save()
        self.assertNotIn('disabled', get_button_html())

        # The user no longer has cluster access.
        allocation_user_attribute.delete()
        self.assertIn('disabled', get_button_html())

    def test_section_hidden_if_viewing_other_user_profile(self):
        """Test that, when logged in as one user but viewing another
        user's User Profile, this section is not displayed."""
        self.user.is_superuser = True
        self.user.save()

        requester = User.objects.create(
            email='other_user@email.com',
            first_name='Other',
            last_name='User',
            username='other_user')
        pending_status = IdentityLinkingRequestStatusChoice.objects.get(
            name='Pending')
        IdentityLinkingRequest.objects.create(
            requester=requester,
            request_time=utc_now_offset_aware(),
            status=pending_status)

        url = reverse(
            'user-profile', kwargs={'viewed_username': requester.username})
        response = self.client.get(url)
        html = response.content.decode('utf-8')
        self.assertIn(requester.username, html)
        self.assertIn(requester.first_name, html)
        self.assertIn(requester.last_name, html)
        self.assertNotIn('Below is your latest request.', html)
        self.assertNotIn('Time Requested', html)
        self.assertNotIn('Time Sent', html)

    def test_time_requested_and_time_sent_correct(self):
        """Test that the correct timestamps are displayed under 'Time
        Requested' and 'Time Sent'."""

        def assert_times(_time_requested, _time_sent):
            """Assert that the values of the 'Time Requested' and 'Time
            Sent' timestamps are correct."""
            _url = self.user_profile_url()
            _response = self.client.get(_url)
            _html = _response.content.decode('utf-8')
            soup = BeautifulSoup(_html, 'html.parser')
            requested_td = str(
                soup.find('td', {'id': 'time-requested-timestamp'}))
            sent_td = str(soup.find('td', {'id': 'time-sent-timestamp'}))
            self.assertIn(_time_requested, requested_td)
            self.assertIn(_time_sent, sent_td)

        def format_date(d):
            """Return a string representing the given datetime in the
            format used by the application.

            Datetimes are stored in UTC, but displayed in
            settings.DISPLAY_TIME_ZONE."""
            return localize(
                d.astimezone(pytz.timezone(settings.DISPLAY_TIME_ZONE)))

        # Create four IdentityLinkingRequests: two pending and two complete.
        status_choices = IdentityLinkingRequestStatusChoice.objects.all()
        n = 4
        for i in range(n):
            offset = timedelta(hours=n - i)
            kwargs = {
                'requester': self.user,
                'request_time': utc_now_offset_aware() - offset,
            }
            if i < 2:
                kwargs['status'] = status_choices.get(name='Pending')
            else:
                kwargs['status'] = status_choices.get(name='Complete')
                kwargs['completion_time'] = (
                    utc_now_offset_aware() - offset + timedelta(minutes=30))
            request = IdentityLinkingRequest.objects.create(**kwargs)
            setattr(self, f'request{i}', request)

        # ID | Request Time | Completion Time | Status
        # 0  | s - 4        | None            | Pending
        # 1  | s - 3        | None            | Pending
        # 2  | s - 2        | s - 1.5         | Complete
        # 3  | s - 1        | s - 0.5         | Complete

        # 1 is the latest of the pending requests.
        time_requested = format_date(self.request1.request_time)
        time_sent = 'Pending'
        assert_times(time_requested, time_sent)
        # Process 1.
        self.request1.completion_time = utc_now_offset_aware()
        self.request1.status = status_choices.get(name='Complete')
        self.request1.save()
        # 0 is the latest of the pending requests.
        time_requested = format_date(self.request0.request_time)
        time_sent = 'Pending'
        assert_times(time_requested, time_sent)
        # Process 0.
        self.request0.completion_time = utc_now_offset_aware()
        self.request0.status = status_choices.get(name='Complete')
        self.request0.save()
        # 0 is the latest of the completed requests.
        time_requested = format_date(self.request0.request_time)
        time_sent = format_date(self.request0.completion_time)
        assert_times(time_requested, time_sent)
        # Delete 0.
        self.request0.delete()
        # 1 is the latest of the completed requests.
        time_requested = format_date(self.request1.request_time)
        time_sent = format_date(self.request1.completion_time)
        assert_times(time_requested, time_sent)
        # Delete 1.
        self.request1.delete()
        # 3 is the latest of the completed requests.
        time_requested = format_date(self.request3.request_time)
        time_sent = format_date(self.request3.completion_time)
        assert_times(time_requested, time_sent)
        # Delete 3.
        self.request3.delete()
        # 2 is the latest of the completed requests.
        time_requested = format_date(self.request2.request_time)
        time_sent = format_date(self.request2.completion_time)
        assert_times(time_requested, time_sent)
        # Delete 2.
        self.request2.delete()
        # No requests remain.
        url = self.user_profile_url()
        response = self.client.get(url)
        html = response.content.decode('utf-8')
        self.assertNotIn('Below is your latest request.', html)
        self.assertNotIn('Time Requested', html)
        self.assertNotIn('Time Sent', html)
