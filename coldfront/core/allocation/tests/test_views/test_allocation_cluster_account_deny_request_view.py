from http import HTTPStatus
from unittest.mock import patch

from django.core import mail

from coldfront.config import settings
from coldfront.core.allocation.tests.test_utils.test_cluster_access_runners import \
    TestClusterAccessRunnersBase
from coldfront.core.allocation.utils_.cluster_access_utils import \
    ClusterAccessRequestDenialRunner
from coldfront.core.utils.common import utc_now_offset_aware
from django.urls import reverse


def raise_exception(*args, **kwargs):
    """Raise an exception."""
    raise Exception('Test exception.')


class TestAllocationClusterAccountDenyRequestView(TestClusterAccessRunnersBase):
    """A class for testing AllocationClusterAccountDenyRequestView."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        # self.create_test_user()
        self.sign_user_access_agreement(self.user0)
        self.password = 'password'
        self.user0.set_password(self.password)
        self.user0.is_superuser = True
        self.user0.save()
        self.client.login(username=self.user0.username, password=self.password)

    def _assert_emails_sent(self):
        email_body = [f'access request under project {self.project0.name}',
                      f'and allocation {self.alloc_obj.allocation.pk} '
                      f'has been denied.']

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]

        self.assertIn('Cluster Access Denied', email.subject)
        for section in email_body:
            self.assertIn(section, email.body)
        self.assertEqual(email.to, [self.user0.email])
        self.assertEqual(email.cc, [self.manager.email])
        self.assertEqual(settings.EMAIL_SENDER, email.from_email)

    def _assert_pre_state(self):
        """Assert that the relevant objects have the expected state,
        assuming that the runner has either not run or not run
        successfully."""
        self.request_obj.refresh_from_db()
        self.assertIsNone(self.request_obj.completion_time)
        self.assertEqual(self.request_obj.status.name, 'Pending - Add')
        self.assertFalse(self._get_cluster_account_status_attr().exists())

    def _assert_post_state(self, pre_time, post_time):
        """Assert that the relevant objects have the expected state,
        assuming that the runner has run successfully."""
        self.request_obj.refresh_from_db()
        self.assertTrue(pre_time < self.request_obj.completion_time < post_time)
        self.assertEqual(self.request_obj.status.name, 'Denied')
        self.assertTrue(self._get_cluster_account_status_attr().exists())
        self.assertEqual(self._get_cluster_account_status_attr().first().value,
                         'Denied')

    @staticmethod
    def view_url(pk):
        """Return the URL to the view for the ClusterAccessRequest
        with the given primary key."""
        return reverse(
            'allocation-cluster-account-deny-request',
            kwargs={'pk': pk})

    def test_success(self):
        """Test that the request status is set to Denied, Cluster Account
        Status AllocationUserAttribute is set to Denied, completion time
        is set, emails are sent, and log messages are written."""
        pre_time = utc_now_offset_aware()
        self.assertEqual(len(mail.outbox), 0)
        self._assert_pre_state()

        url = self.view_url(self.request_obj.pk)
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

        self.assertRedirects(
            response, reverse('allocation-cluster-account-request-list'))

        post_time = utc_now_offset_aware()
        self._assert_post_state(pre_time, post_time)

        self._assert_emails_sent()

    def test_exception_inside_transaction_rollback(self):
        """Test that, when an exception is raised inside the
         transaction, changes made so far are rolled back."""
        self.assertEqual(len(mail.outbox), 0)
        self._assert_pre_state()

        url = self.view_url(self.request_obj.pk)
        with patch.object(
                ClusterAccessRequestDenialRunner,
                'run',
                raise_exception):
            response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

        self.assertRedirects(
            response, reverse('allocation-cluster-account-request-list'))

        self._assert_pre_state()
        self.assertEqual(len(mail.outbox), 0)

    def test_email_failure_no_rollback(self):
        """Test that, when an exception is raised when attempting to
        send an email, changes made so far are not rolled back because
        such an exception is caught."""
        pre_time = utc_now_offset_aware()
        self.assertEqual(len(mail.outbox), 0)
        self._assert_pre_state()

        url = self.view_url(self.request_obj.pk)
        with patch.object(
                ClusterAccessRequestDenialRunner,
                '_send_denial_emails',
                raise_exception):
            response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

        self.assertRedirects(
            response, reverse('allocation-cluster-account-request-list'))

        post_time = utc_now_offset_aware()
        self._assert_post_state(pre_time, post_time)

        self.assertEqual(len(mail.outbox), 0)
