from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.allocation.models import AllocationRenewalRequestStatusChoice
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectAllocationRequestStatusChoice
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.project.utils_.renewal_utils import get_current_allocation_period
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import TestBase
from django.urls import reverse
from http import HTTPStatus
import iso8601


class TestAllocationRenewalRequestReviewDenyView(TestBase):
    """A class for testing AllocationRenewalRequestReviewDenyView."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)

        self.user.is_superuser = True
        self.user.save()

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
        self.allocation_renewal_request = \
            AllocationRenewalRequest.objects.create(
                requester=self.user,
                pi=self.user,
                allocation_period=allocation_period,
                status=under_review_request_status,
                pre_project=project,
                post_project=project,
                request_time=utc_now_offset_aware())

    @staticmethod
    def pi_allocation_renewal_request_review_deny_url(pk):
        """Return the URL for the view for denying the
        AllocationRenewalRequest with the given primary key."""
        return reverse(
            'pi-allocation-renewal-request-review-deny', kwargs={'pk': pk})

    def test_permissions_get(self):
        """Test that the correct users have permissions to perform GET
        requests."""

        def assert_has_access(user, has_access=True, expected_messages=[]):
            """Assert that the given user has or does not have access to
            the URL. Optionally assert that any messages were sent to
            the user."""
            self.client.login(username=user.username, password=self.password)
            url = self.pi_allocation_renewal_request_review_deny_url(
                self.allocation_renewal_request.pk)
            status_code = HTTPStatus.OK if has_access else HTTPStatus.FORBIDDEN
            response = self.client.get(url)
            if expected_messages:
                actual_messages = self.get_message_strings(response)
                for message in expected_messages:
                    self.assertIn(message, actual_messages)
            self.assertEqual(response.status_code, status_code)
            self.client.logout()

        # Superusers should have access.
        self.assertTrue(self.user.is_superuser)
        assert_has_access(self.user)

        # Non-superusers should not have access.
        self.user.is_superuser = False
        self.user.save()
        expected_messages = [
            'You do not have permission to view the previous page.',
        ]
        assert_has_access(
            self.user, has_access=False, expected_messages=expected_messages)

    def test_permissions_post(self):
        """Test that the correct users have permissions to perform POST
        requests."""
        url = self.pi_allocation_renewal_request_review_deny_url(
            self.allocation_renewal_request.pk)
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

    def test_view_blocked_for_inapplicable_statuses(self):
        """Test that requests that are already 'Approved', 'Complete',
        or 'Denied' cannot be modified via the view."""
        url = self.pi_allocation_renewal_request_review_deny_url(
            self.allocation_renewal_request.pk)
        data = {}

        redirect_url = reverse(
            'pi-allocation-renewal-request-detail',
            kwargs={'pk': self.allocation_renewal_request.pk})
        for status_name in ('Approved', 'Complete', 'Denied'):
            self.allocation_renewal_request.status = \
                AllocationRenewalRequestStatusChoice.objects.get(
                    name=status_name)
            # In the 'Denied' case, the view being redirected to expects
            # certain fields in the 'state' field to be set.
            if status_name == 'Denied':
                self.allocation_renewal_request.state['other'] = {
                    'justification': (
                        'This is a test of denying an '
                        'AllocationRenewalRequest.'),
                    'timestamp': utc_now_offset_aware().isoformat(),
                }
            self.allocation_renewal_request.save()
            response = self.client.post(url, data)
            self.assertRedirects(response, redirect_url)
            message = f'You cannot review a request with status {status_name}.'
            self.assertEqual(message, self.get_message_strings(response)[0])

    def test_view_blocked_if_new_project_request_not_denied(self):
        """Test that, if the request has an associated, non-denied
        SavioProjectAllocationRequest for a new Project, the view is
        blocked."""
        url = self.pi_allocation_renewal_request_review_deny_url(
            self.allocation_renewal_request.pk)
        data = {}

        # Create a new Project.
        new_project_name = 'fc_new_project'
        new_project_status = ProjectStatusChoice.objects.get(name='New')
        new_project = Project.objects.create(
            name=new_project_name,
            status=new_project_status,
            title=new_project_name,
            description=f'Description of {new_project_name}.')

        # Create an 'Under Review' SavioProjectAllocationRequest for the new
        # Project.
        under_review_request_status = \
            ProjectAllocationRequestStatusChoice.objects.get(
                name='Under Review')
        new_project_request = SavioProjectAllocationRequest.objects.create(
            requester=self.user,
            allocation_type=SavioProjectAllocationRequest.FCA,
            pi=self.user,
            project=new_project,
            survey_answers={},
            status=under_review_request_status)

        self.allocation_renewal_request.new_project_request = \
            new_project_request
        self.allocation_renewal_request.save()

        redirect_url = reverse(
            'pi-allocation-renewal-request-detail',
            kwargs={'pk': self.allocation_renewal_request.pk})
        response = self.client.post(url, data)
        self.assertRedirects(response, redirect_url)
        message = (
            'Deny the associated Savio Project request first, which should '
            'automatically deny this request.')
        self.assertEqual(message, self.get_message_strings(response)[0])

        # Change its status to 'Denied'.
        new_project_request.status = \
            ProjectAllocationRequestStatusChoice.objects.get(name='Denied')
        new_project_request.save()
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_updates_request_state_and_status(self):
        """Test that a POST request updates the request's 'state' and
        'status' fields."""
        url = self.pi_allocation_renewal_request_review_deny_url(
            self.allocation_renewal_request.pk)
        data = {
            'justification': (
                'This is a test that a POST request updates the request.'),
        }

        pre_time = utc_now_offset_aware()

        redirect_url = reverse(
            'pi-allocation-renewal-request-detail',
            kwargs={'pk': self.allocation_renewal_request.pk})
        response = self.client.post(url, data)
        self.assertRedirects(response, redirect_url)
        message = (
            f'Status for {self.allocation_renewal_request.pk} has been set to '
            f'Denied.')
        self.assertEqual(message, self.get_message_strings(response)[0])

        post_time = utc_now_offset_aware()

        self.allocation_renewal_request.refresh_from_db()
        other = self.allocation_renewal_request.state['other']
        self.assertEqual(other['justification'], data['justification'])
        time = iso8601.parse_date(other['timestamp'])
        self.assertTrue(pre_time <= time <= post_time)
        self.assertEqual(self.allocation_renewal_request.status.name, 'Denied')
