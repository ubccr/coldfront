from coldfront.api.statistics.utils import create_project_allocation
from coldfront.core.project.tests.utils import create_project_and_request
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period
from coldfront.core.project.utils_.renewal_utils import get_next_allowance_year_period
from coldfront.core.resource.models import Resource
from coldfront.core.resource.utils_.allowance_utils.constants import BRCAllowances
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
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
        computing_allowance = self.get_fca_computing_allowance()
        allocation_period = get_current_allowance_year_period()
        self.project, self.new_project_request = \
            create_project_and_request(
                'fc_project', 'New', computing_allowance, allocation_period,
                self.user, self.user, 'Approved - Processing')
        # Create a 'CLUSTER_NAME Compute' Allocation for the Project.
        self.existing_service_units = Decimal('0.00')
        accounting_allocation_objects = create_project_allocation(
            self.project, self.existing_service_units)
        self.compute_allocation = accounting_allocation_objects.allocation
        self.service_units_attribute = \
            accounting_allocation_objects.allocation_attribute

        self.interface = ComputingAllowanceInterface()

    @staticmethod
    def detail_view_url(pk):
        """Return the URL for the detail view for the
        SavioProjectAllocationRequest with the given primary key."""
        return reverse('new-project-request-detail', kwargs={'pk': pk})

    @staticmethod
    def list_view_url():
        """Return the URL for the list view for pending
        SavioProjectAllocationRequests."""
        return reverse('new-project-pending-request-list')

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
        next_allowance_year_allocation_period = \
            get_next_allowance_year_period()
        self.assertIsNotNone(next_allowance_year_allocation_period)
        new_project_request.allocation_period = \
            next_allowance_year_allocation_period
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

    def test_post_approves_and_processes_request_for_null_period_condo(self):
        """Test that a POST request for a new project request (Condo)
        with a null AllocationPeriod is both approved and processed."""
        computing_allowance = Resource.objects.get(name=BRCAllowances.CO)
        project_name_prefix = self.interface.code_from_name(
            computing_allowance.name)

        self.project.name = f'{project_name_prefix}{self.project.name[3:]}'
        self.project.save()
        self.new_project_request.allocation_type = \
            self.interface.name_short_from_name(computing_allowance.name)
        self.new_project_request.computing_allowance = computing_allowance
        self.new_project_request.save()

        self.assertEqual(len(mail.outbox), 0)

        self.user.is_superuser = True
        self.user.save()

        # Set the request's state.
        new_project_request = self.new_project_request
        new_project_request.state['eligibility']['status'] = 'Approved'
        new_project_request.state['readiness']['status'] = 'Approved'
        new_project_request.state['setup']['status'] = 'Complete'
        new_project_request.save()

        # The request has no AllocationPeriod.
        new_project_request.allocation_period = None
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

    def test_post_approves_and_processes_request_for_null_period_recharge(self):
        """Test that a POST request for a new project request (Recharge)
        with a null AllocationPeriod is both approved and processed."""
        computing_allowance = Resource.objects.get(name=BRCAllowances.RECHARGE)
        project_name_prefix = self.interface.code_from_name(
            computing_allowance.name)

        self.project.name = f'{project_name_prefix}{self.project.name[3:]}'
        self.project.save()
        self.new_project_request.allocation_type = \
            self.interface.name_short_from_name(computing_allowance.name)
        self.new_project_request.computing_allowance = computing_allowance
        self.new_project_request.extra_fields = {'num_service_units': 100000}
        self.new_project_request.save()

        self.assertEqual(len(mail.outbox), 0)

        self.user.is_superuser = True
        self.user.save()

        # Set the request's state.
        new_project_request = self.new_project_request
        new_project_request.state['eligibility']['status'] = 'Approved'
        new_project_request.state['readiness']['status'] = 'Approved'
        new_project_request.state['memorandum_signed'] = {'status': 'Complete'}
        new_project_request.state['setup']['status'] = 'Complete'
        new_project_request.save()

        # The request has no AllocationPeriod.
        new_project_request.allocation_period = None
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

    # TODO
