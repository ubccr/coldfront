from coldfront.core.allocation.models import ClusterAccessRequest, \
    AllocationUser, ClusterAccessRequestStatusChoice, AllocationUserAttribute, \
    Allocation
from coldfront.core.user.tests.utils import \
    grant_user_cluster_access_under_test_project
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import TestBase
from django.urls import reverse


class TestAllocationClusterAccountDenyRequestView(TestBase):
    """A class for testing AllocationClusterAccountDenyRequestView."""

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
            'allocation-cluster-account-deny-request',
            kwargs={'pk': pk})

    def test_logs(self):
        """Test that the correct message is written to the log."""
        url = self.view_url(self.request_obj.pk)

        with self.assertLogs('coldfront.core.allocation.utils_.cluster_access_utils', 'INFO') as cm:
            response = self.client.get(url)
        self.assertRedirects(
            response, reverse('allocation-cluster-account-request-list'))

        # Assert that an info message was logged.
        self.assertEqual(len(cm.output), 4)

    def test_denies_request(self):
        """Test that denying the request results in the correct values
        being set."""
        pre_time = utc_now_offset_aware()
        url = self.view_url(self.request_obj.pk)
        self.client.get(url)

        self.request_obj.refresh_from_db()
        self.assertEqual(self.request_obj.status.name, 'Denied')
        self.assertTrue(pre_time <
                        self.request_obj.completion_time <
                        utc_now_offset_aware())

        # Test that the Cluster Account Status Alloc User Attr is
        # created and denied.
        cluster_access = AllocationUserAttribute.objects.filter(
            allocation_attribute_type__name='Cluster Account Status',
            allocation=Allocation.objects.get(project__name='test_project'),
            allocation_user=AllocationUser.objects.get(user=self.user),
            value='Denied')
        self.assertTrue(cluster_access.exists())

    # TODO
