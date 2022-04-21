from coldfront.api.statistics.utils import create_project_allocation
from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.allocation.models import AllocationRenewalRequestStatusChoice
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectAllocationRequestStatusChoice
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period
from coldfront.core.utils.common import display_time_zone_current_date
from coldfront.core.utils.common import format_date_month_name_day_year
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import TestBase
from decimal import Decimal
from django.contrib.auth.models import Permission
from django.contrib.auth.models import User
from django.core import mail
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

        # Create a Project and corresponding Allocation for the user to renew.
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
        self.existing_service_units = Decimal('100000.00')
        accounting_allocation_objects = create_project_allocation(
            project, self.existing_service_units)
        self.compute_allocation = accounting_allocation_objects.allocation
        self.service_units_attribute = \
            accounting_allocation_objects.allocation_attribute

        # Create an AllocationRenewalRequest.
        allocation_period = get_current_allowance_year_period()
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
    def no_op(*args, **kwargs):
        """Do nothing."""
        pass

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

    def test_approved_requests_displayed_as_approved_scheduled(self):
        """Test that requests with the 'Approved' status are displayed
        as 'Approved - Scheduled'."""
        self.allocation_renewal_request.status = \
            AllocationRenewalRequestStatusChoice.objects.get(name='Approved')
        self.allocation_renewal_request.save()
        url = self.pi_allocation_renewal_request_detail_url(
            self.allocation_renewal_request.pk)
        response = self.client.get(url)
        self.assertContains(response, 'Approved - Scheduled')

    def test_permissions_get(self):
        """Test that the correct users have permissions to perform GET
        requests."""
        url = self.pi_allocation_renewal_request_detail_url(
            self.allocation_renewal_request.pk)

        # Superusers should have access.
        self.user.is_superuser = True
        self.user.save()
        self.assert_has_access(url, self.user)
        self.user.is_superuser = False
        self.user.save()

        # The request's PI should have access.
        self.assertEqual(self.allocation_renewal_request.pi, self.user)
        self.assert_has_access(url, self.user)

        # The request's requester should have access. (Set a different PI so
        # that the user is not also the PI.)
        new_pi = User.objects.create(
            email='test_pi@email.com',
            first_name='Test',
            last_name='PI',
            username='test_pi')
        new_pi.set_password(self.password)
        new_pi.save()
        self.allocation_renewal_request.pi = new_pi
        self.allocation_renewal_request.save()
        self.assertNotEqual(self.allocation_renewal_request.pi, self.user)
        self.assertEqual(self.allocation_renewal_request.requester, self.user)
        self.assert_has_access(url, self.user)

        # Users with the permission to view should have access. (Re-fetch the
        # user to avoid permission caching.)
        self.allocation_renewal_request.pi = self.user
        self.allocation_renewal_request.save()
        permission = Permission.objects.get(
            codename='view_allocationrenewalrequest')
        new_pi.user_permissions.add(permission)
        new_pi = User.objects.get(pk=new_pi.pk)
        self.assertNotEqual(self.allocation_renewal_request.pi, new_pi)
        self.assertNotEqual(self.allocation_renewal_request.requester, new_pi)
        self.assertTrue(new_pi.has_perm(f'allocation.{permission.codename}'))
        self.assert_has_access(url, new_pi)

        # Any other user should not have access. (Re-fetch the user to avoid
        # permission caching.)
        new_pi.user_permissions.remove(permission)
        new_pi = User.objects.get(pk=new_pi.pk)
        self.assertNotEqual(self.allocation_renewal_request.pi, new_pi)
        self.assertNotEqual(self.allocation_renewal_request.requester, new_pi)
        self.assertFalse(new_pi.has_perm(f'allocation.{permission.codename}'))
        expected_messages = [
            'You do not have permission to view the previous page.',
        ]
        self.assert_has_access(
            url, new_pi, has_access=False, expected_messages=expected_messages)

    def test_permissions_post(self):
        """Test that the correct users have permissions to perform POST
        requests."""
        url = self.pi_allocation_renewal_request_detail_url(
            self.allocation_renewal_request.pk)
        data = {}

        # Users, even those with the permission to view, or who are the
        # requester or PI, should not have access.
        self.assertEqual(self.allocation_renewal_request.pi, self.user)
        self.assertEqual(self.allocation_renewal_request.requester, self.user)
        permission = Permission.objects.get(
            codename='view_allocationrenewalrequest')
        self.user.user_permissions.add(permission)
        self.user = User.objects.get(pk=self.user.pk)
        self.assertTrue(
            self.user.has_perm(f'allocation.{permission.codename}'))
        response = self.client.post(url, data)
        redirect_url = reverse(
            'pi-allocation-renewal-request-detail',
            kwargs={'pk': self.allocation_renewal_request.pk})
        self.assertRedirects(response, redirect_url)
        message = 'You do not have permission to POST to this page.'
        self.assertEqual(message, self.get_message_strings(response)[0])

        # Superusers should have access.
        self.user.is_superuser = True
        self.user.save()
        response = self.client.post(url, data)
        self.assertRedirects(response, redirect_url)
        message = 'Please complete the checklist before final activation.'
        self.assertEqual(message, self.get_message_strings(response)[0])

    def test_post_approves_and_processes_request_for_started_period(self):
        """Test that a POST request for a renewal request under an
        AllocationPeriod that has already started is both approved and
        processed."""
        self.assertEqual(len(mail.outbox), 0)

        self.user.is_superuser = True
        self.user.save()

        # Set the request's eligibility state.
        allocation_renewal_request = self.allocation_renewal_request
        allocation_renewal_request.state['eligibility']['status'] = 'Approved'
        allocation_renewal_request.save()

        # The request's AllocationPeriod has already started.
        self.assertLessEqual(
            allocation_renewal_request.allocation_period.start_date,
            display_time_zone_current_date())

        pre_time = utc_now_offset_aware()

        url = self.pi_allocation_renewal_request_detail_url(
            allocation_renewal_request.pk)
        data = {}
        response = self.client.post(url, data)

        post_time = utc_now_offset_aware()

        # The view should redirect to the list of requests and display a
        # message.
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(
            response.url, self.pi_allocation_renewal_request_list_url())
        message = f'PI {self.user.username}\'s allocation has been renewed.'
        self.assertEqual(message, self.get_message_strings(response)[0])

        # The request's status should have been set to 'Approved' and then to
        # 'Complete', and its approval_time and completion_time should have
        # been set. AllocationRenewalProcessingRunner verifies that the request
        # has the 'Approved' status. Therefore, if processing completed, the
        # request must have had the 'Approved' status at the time.
        allocation_renewal_request.refresh_from_db()
        self.assertEqual(allocation_renewal_request.status.name, 'Complete')
        self.assertTrue(
            pre_time <=
            allocation_renewal_request.approval_time <=
            allocation_renewal_request.completion_time <=
            post_time)

        # One email about processing should have been sent; an email about
        # approval should not have been sent.
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn(f'{allocation_renewal_request} Processed', email.subject)

        # The 'CLUSTER_NAME Compute' Allocation's Service Units should have
        # increased.
        expected_num_service_units = (
            self.existing_service_units +
            allocation_renewal_request.num_service_units)
        self.service_units_attribute.refresh_from_db()
        self.assertEqual(
            expected_num_service_units,
            Decimal(self.service_units_attribute.value))

    def test_post_approves_not_processes_request_for_non_started_period(self):
        """Test that a POST request for a renewal request under an
        AllocationPeriod that has not yet started is approved, but not
        processed."""
        self.assertEqual(len(mail.outbox), 0)

        self.user.is_superuser = True
        self.user.save()

        # Set the request's eligibility state.
        allocation_renewal_request = self.allocation_renewal_request
        allocation_renewal_request.state['eligibility']['status'] = 'Approved'
        allocation_renewal_request.save()

        # Set the request's AllocationPeriod to one that has not already
        # started.
        next_allowance_year_allocation_period = \
            AllocationPeriod.objects.filter(
                name__startswith='Allowance Year',
                start_date__gt=display_time_zone_current_date()).first()
        self.assertIsNotNone(next_allowance_year_allocation_period)
        allocation_renewal_request.allocation_period = \
            next_allowance_year_allocation_period
        allocation_renewal_request.save()

        pre_time = utc_now_offset_aware()

        url = self.pi_allocation_renewal_request_detail_url(
            allocation_renewal_request.pk)
        data = {}
        response = self.client.post(url, data)

        post_time = utc_now_offset_aware()

        # The view should redirect to the list of requests and display a
        # message.
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(
            response.url, self.pi_allocation_renewal_request_list_url())
        formatted_start_date = format_date_month_name_day_year(
            next_allowance_year_allocation_period.start_date)
        message = (
            f'PI {self.user.username}\'s allocation is scheduled for renewal '
            f'on {formatted_start_date}.')
        self.assertEqual(message, self.get_message_strings(response)[0])

        # The request's status should have been set to 'Approved', and its
        # approval_time, but not its completion_time, should have been set.
        allocation_renewal_request.refresh_from_db()
        self.assertEqual(allocation_renewal_request.status.name, 'Approved')
        self.assertTrue(
            pre_time <= allocation_renewal_request.approval_time <= post_time)
        self.assertIsNone(allocation_renewal_request.completion_time)

        # One email about approval should have been sent; an email about
        # processing should not have been sent.
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn(f'{allocation_renewal_request} Approved', email.subject)

        # The 'CLUSTER_NAME Compute' Allocation's Service Units should not have
        # increased.
        expected_num_service_units = self.existing_service_units
        self.service_units_attribute.refresh_from_db()
        self.assertEqual(
            expected_num_service_units,
            Decimal(self.service_units_attribute.value))

    @patch(
        'coldfront.core.project.utils_.renewal_utils.'
        'AllocationRenewalProcessingRunner.run')
    def test_post_blocked_until_checklist_complete_existing_project(self,
                                                                    mock_method):
        """Test that, for a request whose post_project already exists, a
        POST request raises an error until the PI's eligibility is
        approved."""
        # Patch the method for running the processing to do nothing.
        mock_method.side_effect = self.no_op

        url = self.pi_allocation_renewal_request_detail_url(
            self.allocation_renewal_request.pk)
        data = {}

        self.user.is_superuser = True
        self.user.save()

        # The PI's eligibility has not been approved.
        eligibility = self.allocation_renewal_request.state['eligibility']
        self.assertNotEqual(eligibility['status'], 'Approved')
        response = self.client.post(url, data)
        redirect_url = reverse(
            'pi-allocation-renewal-request-detail',
            kwargs={'pk': self.allocation_renewal_request.pk})
        self.assertRedirects(response, redirect_url)
        message = 'Please complete the checklist before final activation.'
        self.assertEqual(message, self.get_message_strings(response)[0])

        # Approve it.
        eligibility['status'] = 'Approved'
        self.allocation_renewal_request.save()
        response = self.client.post(url, data)
        redirect_url = reverse('pi-allocation-renewal-pending-request-list')
        self.assertRedirects(response, redirect_url)
        message = f'PI {self.user.username}\'s allocation has been renewed.'
        self.assertEqual(message, self.get_message_strings(response)[0])

    @patch(
        'coldfront.core.project.utils_.renewal_utils.'
        'AllocationRenewalProcessingRunner.run')
    def test_post_blocked_until_checklist_complete_new_project(self,
                                                               mock_method):
        """Test that, for a request whose post_project does not already
        exist, a POST request raises an error until the associated
        request is approved and processed."""
        # Patch the method for running the processing to do nothing.
        mock_method.side_effect = self.no_op

        url = self.pi_allocation_renewal_request_detail_url(
            self.allocation_renewal_request.pk)
        data = {}

        self.user.is_superuser = True
        self.user.save()

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

        # Update the renewal request so that it references the new objects.
        self.allocation_renewal_request.post_project = new_project
        self.allocation_renewal_request.new_project_request = \
            new_project_request
        self.allocation_renewal_request.save()

        # The new project request is not 'Approved - Complete'.
        status_name = new_project_request.status.name
        self.assertNotEqual(status_name, 'Approved - Complete')
        response = self.client.post(url, data)
        redirect_url = reverse(
            'pi-allocation-renewal-request-detail',
            kwargs={'pk': self.allocation_renewal_request.pk})
        self.assertRedirects(response, redirect_url)
        message = 'Please complete the checklist before final activation.'
        self.assertEqual(message, self.get_message_strings(response)[0])

        # Approve and complete it.
        new_project_request.status = \
            ProjectAllocationRequestStatusChoice.objects.get(
                name='Approved - Complete')
        new_project_request.save()
        response = self.client.post(url, data)
        redirect_url = reverse('pi-allocation-renewal-pending-request-list')
        self.assertRedirects(response, redirect_url)
        message = f'PI {self.user.username}\'s allocation has been renewed.'
        self.assertEqual(message, self.get_message_strings(response)[0])
