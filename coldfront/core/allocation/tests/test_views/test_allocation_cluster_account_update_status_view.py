from coldfront.core.user.tests.utils import grant_user_cluster_access_under_test_project
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
        self.attribute = grant_user_cluster_access_under_test_project(
            self.user)
        self.attribute.value = 'Pending - Add'
        self.attribute.save()

    @staticmethod
    def view_url(attribute_pk):
        """Return the URL to the view for the AllocationUserAttribute
        with the given primary key."""
        return reverse(
            'allocation-cluster-account-update-status',
            kwargs={'pk': attribute_pk})

    def test_logs_request_user(self):
        """Test that a message is written to the log noting which user
        made the request to update the status."""
        url = self.view_url(self.attribute.pk)
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
            f'Status" AllocationUserAttribute {self.attribute.pk} from '
            f'"Pending - Add" to "{data["status"]}".')
        self.assertIn(expected_log_message, cm.output[0])

    def test_updates_value(self):
        """Test that updating the status results in the correct value
        being set."""
        for status in ('Pending - Add', 'Processing'):
            url = self.view_url(self.attribute.pk)
            data = {
                'status': status,
            }
            self.client.post(url, data)

            self.attribute.refresh_from_db()
            self.assertEqual(self.attribute.value, status)

    # TODO
