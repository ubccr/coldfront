from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.allocation.models import AllocationRenewalRequestStatusChoice
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.utils_.renewal_utils import get_current_allocation_period
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import TestBase
from django.urls import reverse
from http import HTTPStatus
from unittest.mock import patch


class TestAllocationRenewalRequestDetailView(TestBase):
    """A class for testing AllocationRenewalRequestDetailView."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)

    @staticmethod
    def pi_allocation_renewal_request_detail_url(pk):
        """Return the URL for the detail view for the
        AllocationRenewalRequest with the given primary key."""
        return reverse(
            'pi-allocation-renewal-request-detail', kwargs={'pk': pk})

    @staticmethod
    def pi_allocation_renewal_request_list_url():
        """Return the URL for the list view of
        AllocationRenewalRequests."""
        return reverse('pi-allocation-renewal-pending-request-list')

    @patch(
        'coldfront.core.project.utils_.renewal_utils.'
        'AllocationRenewalProcessingRunner.run')
    def test_post_sets_request_approval_time(self, mock_method):
        """Test that a POST request sets the approval_time of the
        renewal request before processing."""

        # Patch the method for running the processing to do nothing.
        def mocked_method_side_effect(*args):
            """Do nothing."""
            pass

        mock_method.side_effect = mocked_method_side_effect

        # Create a Project for the user to renew.
        project_name = 'fc_project'
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
            user=self.user)

        # Create an AllocationRenewalRequest.
        allocation_period = get_current_allocation_period()
        under_review_request_status = \
            AllocationRenewalRequestStatusChoice.objects.get(
                name='Under Review')
        allocation_renewal_request = AllocationRenewalRequest.objects.create(
            requester=self.user,
            pi=self.user,
            allocation_period=allocation_period,
            status=under_review_request_status,
            pre_project=project,
            post_project=project,
            request_time=utc_now_offset_aware())

        # Set the request's eligibility state.
        allocation_renewal_request.state['eligibility']['status'] = 'Approved'
        allocation_renewal_request.save()

        pre_time = utc_now_offset_aware()

        url = self.pi_allocation_renewal_request_detail_url(
            allocation_renewal_request.pk)
        data = {}
        response = self.client.post(url, data)

        post_time = utc_now_offset_aware()

        # The view should redirect to the list of requests.
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(
            response.url, self.pi_allocation_renewal_request_list_url())

        # Because of the patch, the request's status should be 'Approved'
        # rather than 'Complete'.
        allocation_renewal_request.refresh_from_db()
        self.assertEqual(allocation_renewal_request.status.name, 'Approved')
        self.assertTrue(
            pre_time <= allocation_renewal_request.approval_time <= post_time)

    # TODO
