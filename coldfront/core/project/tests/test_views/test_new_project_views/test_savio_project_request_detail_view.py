from coldfront.api.statistics.utils import create_project_allocation
from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.project.tests.utils import create_fca_project_and_request
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period
from coldfront.core.utils.common import display_time_zone_current_date
from coldfront.core.utils.common import format_date_month_name_day_year
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import TestBase
from decimal import Decimal

from django.core import mail
from django.urls import reverse
from http import HTTPStatus


class TestSavioProjectRequestDetailView(TestBase):
    """A class for testing SavioProjectRequestDetailView."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)

        # Create a Project and a corresponding new project request.
        allocation_period = get_current_allowance_year_period()
        self.project, self.new_project_request = \
            create_fca_project_and_request(
                'fc_project', 'New', allocation_period, self.user, self.user,
                'Approved - Processing')
        # Create a 'CLUSTER_NAME Compute' Allocation for the Project.
        self.existing_service_units = Decimal('0.00')
        accounting_allocation_objects = create_project_allocation(
            self.project, self.existing_service_units)
        self.compute_allocation = accounting_allocation_objects.allocation
        self.service_units_attribute = \
            accounting_allocation_objects.allocation_attribute

    @staticmethod
    def detail_view_url(pk):
        """Return the URL for the detail view for the
        SavioProjectAllocationRequest with the given primary key."""
        return reverse('savio-project-request-detail', kwargs={'pk': pk})

    @staticmethod
    def list_view_url():
        """Return the URL for the list view for pending
        SavioProjectAllocationRequests."""
        return reverse('savio-project-pending-request-list')

    def test_post_approves_and_processes_request_for_started_period(self):
        """Test that a POST request for a new project request under an
        AllocationPeriod that has already started is both approved and
        processed."""
        self.assertEqual(len(mail.outbox), 0)

        self.user.is_superuser = True
        self.user.save()

        # Set the request's state.
        new_project_request = self.new_project_request
        new_project_request.state['eligibility']['status'] = 'Approved'
        new_project_request.state['readiness']['status'] = 'Approved'
        new_project_request.state['setup']['status'] = 'Complete'
        new_project_request.save()

        # The request's AllocationPeriod has already started.
        self.assertLessEqual(
            new_project_request.allocation_period.start_date,
            display_time_zone_current_date())

        pre_time = utc_now_offset_aware()

        url = self.detail_view_url(new_project_request.pk)
        data = {}
        response = self.client.post(url, data)

        post_time = utc_now_offset_aware()

        # The view should redirect to the list of requests and display a
        # message.
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(response.url, self.list_view_url())
        message = (
            f'Project {new_project_request.project.name} and its Allocation '
            f'have been activated')
        self.assertIn(message, self.get_message_strings(response)[0])

        # The request's status should have been set to 'Approved - Complete',
        # and its approval_time and completion_time should have been set.
        new_project_request.refresh_from_db()
        self.assertEqual(
            new_project_request.status.name, 'Approved - Complete')
        self.assertTrue(
            pre_time <=
            new_project_request.approval_time <=
            new_project_request.completion_time <=
            post_time)

        # One email about processing should have been sent; an email about
        # approval should not have been sent.
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn(
            (f'New Project Request ({new_project_request.project.name}) '
             f'Processed'),
            email.subject)

        # The 'CLUSTER_NAME Compute' Allocation's Service Units should have
        # increased.
        self.service_units_attribute.refresh_from_db()
        self.assertGreater(
            Decimal(self.service_units_attribute.value),
            self.existing_service_units)

    def test_post_approves_not_processes_request_for_non_started_period(self):
        """Test that a POST request for a new project request under an
        AllocationPeriod that has not yet started is approved, but not
        processed."""
        self.assertEqual(len(mail.outbox), 0)

        self.user.is_superuser = True
        self.user.save()

        # Set the request's state.
        new_project_request = self.new_project_request
        new_project_request.state['eligibility']['status'] = 'Approved'
        new_project_request.state['readiness']['status'] = 'Approved'
        new_project_request.state['setup']['status'] = 'Complete'
        new_project_request.save()

        # Set the request's AllocationPeriod to one that has not already
        # started.
        next_allowance_year_period = \
            AllocationPeriod.objects.filter(
                name__startswith='Allowance Year',
                start_date__gt=display_time_zone_current_date()).first()
        self.assertIsNotNone(next_allowance_year_period)
        new_project_request.allocation_period = next_allowance_year_period
        new_project_request.save()

        pre_time = utc_now_offset_aware()

        url = self.detail_view_url(new_project_request.pk)
        data = {}
        response = self.client.post(url, data)

        post_time = utc_now_offset_aware()

        # The view should redirect to the list of requests and display a
        # message.
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(response.url, self.list_view_url())
        formatted_start_date = format_date_month_name_day_year(
            new_project_request.allocation_period.start_date)
        message = (
            f'Project {new_project_request.project.name} and its Allocation '
            f'are scheduled for activation on {formatted_start_date}')
        self.assertIn(message, self.get_message_strings(response)[0])

        # The request's status should have been set to 'Approved - Scheduled',
        # and its approval_time, but not its completion_time, should have been
        # set.
        new_project_request.refresh_from_db()
        self.assertEqual(
            new_project_request.status.name, 'Approved - Scheduled')
        self.assertTrue(
            pre_time <= new_project_request.approval_time <= post_time)
        self.assertIsNone(new_project_request.completion_time)

        # One email about approval should have been sent; an email about
        # processing should not have been sent.
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn(
            (f'New Project Request ({new_project_request.project.name}) '
             f'Approved'),
            email.subject)

        # The 'CLUSTER_NAME Compute' Allocation's Service Units should not have
        # increased.
        self.service_units_attribute.refresh_from_db()
        self.assertEqual(
            Decimal(self.service_units_attribute.value),
            self.existing_service_units)

    # TODO
