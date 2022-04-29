from coldfront.api.statistics.utils import create_project_allocation
from coldfront.core.allocation.models import AllocationAdditionRequest
from coldfront.core.allocation.models import AllocationAdditionRequestStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.utils.tests.test_base import TestBase

from decimal import Decimal
from django.contrib.auth.models import Permission
from django.contrib.auth.models import User
from django.urls import reverse
from unittest.mock import patch


class TestAllocationAdditionRequestDetailView(TestBase):
    """A class for testing AllocationAdditionRequestDetailView."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)

        self.project = self.create_active_project_with_pi(
            'ac_project', self.user)

        self.allocation_addition_request = \
            AllocationAdditionRequest.objects.create(
                requester=self.user,
                project=self.project,
                status=AllocationAdditionRequestStatusChoice.objects.get(
                    name='Under Review'),
                num_service_units=Decimal('1000.00'))

    @staticmethod
    def no_op(*args, **kwargs):
        """Do nothing."""
        pass

    @staticmethod
    def request_detail_url(pk):
        """Return the URL for the detail view for the
        AllocationAdditionRequest with the given primary key."""
        return reverse(
            'service-units-purchase-request-detail', kwargs={'pk': pk})

    def test_permissions_get(self):
        """Test that the correct users have permissions to perform GET
        requests."""
        url = self.request_detail_url(self.allocation_addition_request.pk)

        # Superusers should have access.
        self.user.is_superuser = True
        self.user.save()
        self.assert_has_access(url, self.user)
        self.user.is_superuser = False
        self.user.save()

        # The Project's PIs should have access.
        project_user = ProjectUser.objects.get(
            project=self.project, user=self.user)
        self.assertEqual(project_user.role.name, 'Principal Investigator')
        self.assert_has_access(url, self.user)

        # The Project's Managers should have access.
        project_user.role = ProjectUserRoleChoice.objects.get(name='Manager')
        project_user.save()
        self.assert_has_access(url, self.user)

        # Users with the permission to view should have access. (Re-fetch the
        # user to avoid permission caching.)
        project_user.delete()
        permission = Permission.objects.get(
            codename='view_allocationadditionrequest')
        self.user.user_permissions.add(permission)
        self.user = User.objects.get(pk=self.user.pk)
        self.assertTrue(
            self.user.has_perm(f'allocation.{permission.codename}'))
        self.assert_has_access(url, self.user)

        # Any other user should not have access. (Re-fetch the user to avoid
        # permission caching.)
        self.user.user_permissions.remove(permission)
        self.user = User.objects.get(pk=self.user.pk)
        self.assertFalse(
            self.user.has_perm(f'allocation.{permission.codename}'))
        expected_messages = [
            'You must be an active PI or manager of the Project.',
        ]
        self.assert_has_access(
            url, self.user, has_access=False,
            expected_messages=expected_messages)

    def test_permissions_post(self):
        """Test that the correct users have permissions to perform POST
        requests."""
        url = self.request_detail_url(self.allocation_addition_request.pk)
        data = {}

        # Users, even those with the permission to view, or who are PIs or
        # Managers, should not have access.
        self.assertTrue(
            ProjectUser.objects.filter(
                project=self.project,
                user=self.user,
                role__name='Principal Investigator').exists())
        permission = Permission.objects.get(
            codename='view_allocationrenewalrequest')
        self.user.user_permissions.add(permission)
        self.user = User.objects.get(pk=self.user.pk)
        self.assertTrue(
            self.user.has_perm(f'allocation.{permission.codename}'))
        response = self.client.post(url, data)
        redirect_url = self.request_detail_url(
            self.allocation_addition_request.pk)
        self.assertRedirects(response, redirect_url)
        message = 'You do not have permission to access this page.'
        self.assertEqual(message, self.get_message_strings(response)[0])

        # Superusers should have access.
        self.user.is_superuser = True
        self.user.save()
        response = self.client.post(url, data)
        self.assertRedirects(response, redirect_url)
        message = 'Please complete the checklist before final activation.'
        self.assertEqual(message, self.get_message_strings(response)[0])

    @patch(
        'coldfront.core.project.utils_.addition_utils.'
        'AllocationAdditionProcessingRunner.run')
    def test_post_blocked_until_checklist_complete(self, mock_method):
        """Test that a POST request raises an error until the checklist
        of administrator tasks is complete."""
        create_project_allocation(self.project, Decimal('1000.00'))

        # Patch the method for running the processing to do nothing.
        mock_method.side_effect = self.no_op

        url = self.request_detail_url(self.allocation_addition_request.pk)
        data = {}

        self.user.is_superuser = True
        self.user.save()

        # The status of the MOU has not been confirmed.
        memorandum_signed = self.allocation_addition_request.state[
            'memorandum_signed']
        self.assertNotEqual(memorandum_signed['status'], 'Complete')
        response = self.client.post(url, data)
        redirect_url = self.request_detail_url(
            self.allocation_addition_request.pk)
        self.assertRedirects(response, redirect_url)
        message = 'Please complete the checklist before final activation.'
        self.assertEqual(message, self.get_message_strings(response)[0])

        # Confirm it.
        memorandum_signed['status'] = 'Complete'
        self.allocation_addition_request.save()
        response = self.client.post(url, data)
        redirect_url = reverse('service-units-purchase-pending-request-list')
        self.assertRedirects(response, redirect_url)
        message = self.get_message_strings(response)[0]
        self.assertIn('allocation has been set to', message)
        self.assertIn('usage has been reset', message)
