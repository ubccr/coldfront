from coldfront.core.allocation.models import AllocationRenewalRequest
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


class TestAllocationRenewalRequestUnderProjectView(TestBase):
    """A class for testing AllocationRenewalRequestUnderProjectView."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)

    @staticmethod
    def project_detail_url(pk):
        """Return the URL for the detail view for the Project with the
        given primary key."""
        return reverse('project-detail', kwargs={'pk': pk})

    @staticmethod
    def project_renew_url(pk):
        """Return the URL for the requesting to renew a PI's
        allocation under the Project with the given primary key."""
        return reverse('project-renew', kwargs={'pk': pk})

    def test_post_sets_request_request_time(self):
        """Test that a POST request sets the request_time of the renewal
        request."""
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
        project_user = ProjectUser.objects.create(
            project=project,
            role=pi_role,
            status=active_project_user_status,
            user=self.user)

        pre_time = utc_now_offset_aware()

        allocation_period = get_current_allocation_period()

        view_name = 'allocation_renewal_request_under_project_view'
        current_step_key = f'{view_name}-current_step'

        allocation_period_form_data = {
            '0-allocation_period': allocation_period.pk,
            current_step_key: '0',
        }
        pi_selection_form_data = {
            '1-PI': project_user.pk,
            current_step_key: '1',
        }
        review_and_submit_form_data = {
            '2-confirmation': True,
            current_step_key: '2',
        }
        form_data = [
            allocation_period_form_data,
            pi_selection_form_data,
            review_and_submit_form_data,
        ]

        url = self.project_renew_url(project.pk)
        for i, data in enumerate(form_data):
            response = self.client.post(url, data)
            if i == len(form_data) - 1:
                self.assertRedirects(
                    response, self.project_detail_url(project.pk))
            else:
                self.assertEqual(response.status_code, HTTPStatus.OK)

        post_time = utc_now_offset_aware()

        requests = AllocationRenewalRequest.objects.all()
        self.assertEqual(requests.count(), 1)
        request = requests.first()
        self.assertTrue(pre_time <= request.request_time <= post_time)
