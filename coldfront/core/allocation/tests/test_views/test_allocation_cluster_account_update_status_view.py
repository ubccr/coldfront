from coldfront.core.allocation.models import ClusterAccessRequest, \
    AllocationUser, ClusterAccessRequestStatusChoice
from coldfront.core.user.tests.utils import \
    grant_user_cluster_access_under_test_project
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import TestBase
from django.urls import reverse


class TestAllocationClusterAccountUpdateStatusView(TestBase):
    """A class for testing AllocationClusterAccountUpdateStatusView."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)
        self.user.is_superuser = True
        self.user.save()
        attribute = grant_user_cluster_access_under_test_project(
            self.user)
        attribute.delete()

        # Create ClusterAccessRequest
        self.request_obj = ClusterAccessRequest.objects.create(
            allocation_user=AllocationUser.objects.get(user=self.user),
            status=ClusterAccessRequestStatusChoice.objects.get(
                name='Pending - Add'),
            request_time=utc_now_offset_aware())

    @staticmethod
    def view_url(pk):
        """Return the URL to the view for the ClusterAccessRequest
        with the given primary key."""
        return reverse(
            'allocation-cluster-account-update-status',
            kwargs={'pk': pk})

    def test_logs_request_user(self):
        """Test that the correct message is written to the log."""
        url = self.view_url(self.request_obj.pk)
        data = {
            'status': 'Processing',
        }
        with self.assertLogs('coldfront.core.allocation.views', 'INFO') as cm:
            response = self.client.post(url, data)
        self.assertRedirects(
            response, reverse('allocation-cluster-account-request-list'))

        # Assert that an info message was logged.
        self.assertEqual(len(cm.output), 1)
        expected_log_message = (
            f'Superuser {self.user.pk} changed the value of "Cluster Account '
            f'Status" AllocationUserAttribute {self.request_obj.pk} from '
            f'"Pending - Add" to "{data["status"]}".')
        self.assertIn(expected_log_message, cm.output[0])

    def test_updates_value(self):
        """Test that updating the status results in the correct value
        being set."""
        for status in ('Pending - Add', 'Processing'):
            url = self.view_url(self.request_obj.pk)
            data = {
                'status': status,
            }
            self.client.post(url, data)

            self.request_obj.refresh_from_db()
            self.assertEqual(self.request_obj.status.name, status)

    # TODO
