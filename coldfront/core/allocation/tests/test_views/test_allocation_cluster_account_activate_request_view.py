from http import HTTPStatus
from unittest.mock import patch

from django.core import mail

from coldfront.config import settings
from coldfront.core.allocation.models import ClusterAccessRequestStatusChoice
from coldfront.core.allocation.tests.test_utils.test_cluster_access_runners import \
    TestClusterAccessRunnersBase
from coldfront.core.allocation.utils_.cluster_access_utils import \
    ClusterAccessRequestCompleteRunner
from coldfront.core.utils.common import utc_now_offset_aware
from django.urls import reverse


def raise_exception(*args, **kwargs):
    """Raise an exception."""
    raise Exception('Test exception.')


class TestAllocationClusterAccountActivateRequestView(TestClusterAccessRunnersBase):
    """A class for testing AllocationClusterAccountActivateRequestView."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.sign_user_access_agreement(self.user0)
        self.password = 'password'
        self.user0.set_password(self.password)
        self.user0.is_superuser = True
        self.user0.save()
        
        self.user0.userprofile.cluster_uid = None
        self.user0.userprofile.save()
        
        self.client.login(username=self.user0.username, password=self.password)
        self.request_obj.status = \
            ClusterAccessRequestStatusChoice.objects.get(name='Processing')
        self.request_obj.save()
        
        self.new_username = 'new_username'
        self.cluster_uid = '1234'
        
        self.data = {
            'username': self.new_username,
            'cluster_uid': self.cluster_uid
        }

    def _assert_emails_sent(self):
        email_body = [f'now has access to the project {self.project0.name}.',
                      f'supercluster username is - {self.new_username}',
                      f'If this is the first time you are accessing',
                      f'start with the below Logging In page:']

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]

        self.assertIn('Cluster Access Activated', email.subject)
        for section in email_body:
            self.assertIn(section, email.body)
        self.assertEqual(email.to, [self.user0.email])
        self.assertEqual(email.cc, [self.manager.email])
        self.assertEqual(settings.EMAIL_SENDER, email.from_email)

    def _refresh_objects(self):
        self.request_obj.refresh_from_db()
        self.user0.refresh_from_db()
        self.alloc_obj.allocation.refresh_from_db()
        self.alloc_user_obj.allocation_user.refresh_from_db()
        self.alloc_user_obj.allocation_user_attribute.refresh_from_db()

    def _assert_pre_state(self):
        """Assert that the relevant objects have the expected state,
        assuming that the runner has either not run or not run
        successfully."""
        self._refresh_objects()
        self.assertIsNone(self.user0.userprofile.cluster_uid)
        self.assertNotEqual(self.user0.username, self.new_username)
        self.assertIsNone(self.request_obj.completion_time)
        self.assertEqual(self.request_obj.status.name, 'Processing')
        self.assertNotEqual(self.alloc_user_obj.allocation_user_attribute.value,
                            self.alloc_obj.allocation_attribute.value)
        self.assertFalse(self._get_cluster_account_status_attr().exists())

    def _assert_post_state(self, pre_time, post_time):
        """Assert that the relevant objects have the expected state,
        assuming that the runner has run successfully."""
        self._refresh_objects()
        self.assertEqual(self.user0.userprofile.cluster_uid, self.cluster_uid)
        self.assertEqual(self.user0.username, self.new_username)
        self.assertTrue(pre_time < self.request_obj.completion_time < post_time)
        self.assertEqual(self.request_obj.status.name, 'Complete')
        self.assertEqual(self.user0.userprofile.cluster_uid, self.cluster_uid)
        self.assertEqual(self.user0.username, self.new_username)
        self.assertEqual(self.alloc_user_obj.allocation_user_attribute.value,
                         self.alloc_obj.allocation_attribute.value)
        self.assertTrue(self._get_cluster_account_status_attr().exists())
        self.assertEqual(self._get_cluster_account_status_attr().first().value,
                         'Active')

    @staticmethod
    def view_url(pk):
        """Return the URL to the view for the ClusterAccessRequest
        with the given primary key."""
        return reverse(
            'allocation-cluster-account-activate-request',
            kwargs={'pk': pk})

    def test_exception_inside_transaction_rollback(self):
        """Test that, when an exception is raised inside the
         transaction, changes made so far are rolled back."""
        self.assertEqual(len(mail.outbox), 0)
        self._assert_pre_state()

        url = self.view_url(self.request_obj.pk)
        with patch.object(
                ClusterAccessRequestCompleteRunner,
                'run',
                raise_exception):
            response = self.client.post(url, self.data)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

        self.assertRedirects(
            response, reverse('allocation-cluster-account-request-list'))

        self._assert_pre_state()
        self.assertEqual(len(mail.outbox), 0)

    def test_success(self):
        """Test that the request status is set to Complete, Cluster Account
        Status AllocationUserAttribute is set to Active, completion time
        is set, emails are sent."""
        pre_time = utc_now_offset_aware()
        self.assertEqual(len(mail.outbox), 0)
        self._assert_pre_state()

        url = self.view_url(self.request_obj.pk)
        response = self.client.post(url, self.data)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

        self.assertRedirects(
            response, reverse('allocation-cluster-account-request-list'))

        post_time = utc_now_offset_aware()
        self._assert_post_state(pre_time, post_time)

        self._assert_emails_sent()

    def test_email_failure_no_rollback(self):
        """Test that, when an exception is raised when attempting to
        send an email, changes made so far are not rolled back because
        such an exception is caught."""
        pre_time = utc_now_offset_aware()
        self.assertEqual(len(mail.outbox), 0)
        self._assert_pre_state()

        url = self.view_url(self.request_obj.pk)
        with patch.object(
                ClusterAccessRequestCompleteRunner,
                '_send_complete_emails',
                raise_exception):
            response = self.client.post(url, self.data)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

        self.assertRedirects(
            response, reverse('allocation-cluster-account-request-list'))

        post_time = utc_now_offset_aware()
        self._assert_post_state(pre_time, post_time)

        self.assertEqual(len(mail.outbox), 0)
