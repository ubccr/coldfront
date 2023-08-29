from http import HTTPStatus

from django.conf import settings
from django.core import mail
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse

from flags.state import flag_enabled

from coldfront.api.statistics.utils import create_project_allocation
from coldfront.core.billing.models import BillingActivity
from coldfront.core.billing.models import BillingProject
from coldfront.core.project.tests.utils import create_project_and_request
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period
from coldfront.core.project.utils_.renewal_utils import get_next_allowance_year_period
from coldfront.core.resource.models import Resource
from coldfront.core.resource.utils_.allowance_utils.constants import BRCAllowances
from coldfront.core.resource.utils_.allowance_utils.constants import LRCAllowances
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.utils.common import display_time_zone_current_date
from coldfront.core.utils.common import format_date_month_name_day_year
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import TestBase
from decimal import Decimal


class TestSavioProjectRequestDetailView(TestBase):
    """A class for testing SavioProjectRequestDetailView."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()

        if flag_enabled('LRC_ONLY'):
            self.user.email = 'test_user@lbl.gov'
            self.user.save()

        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)

        self.interface = ComputingAllowanceInterface()

        # Create a Project and a corresponding new project request.
        computing_allowance = self.get_predominant_computing_allowance()
        prefix = self.interface.code_from_name(computing_allowance.name)
        allocation_period = get_current_allowance_year_period()
        self.project, self.new_project_request = \
            create_project_and_request(
                f'{prefix}_project', 'New', computing_allowance,
                allocation_period, self.user, self.user,
                'Approved - Processing')

        self.new_project_request.billing_activity = \
            BillingActivity.objects.create(
                billing_project=BillingProject.objects.create(
                    identifier='000000'),
                identifier='000')
        self.new_project_request.save()

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
        # approval should not have been sent. In addition, an email about a new
        # cluster access request should have been sent.
        self.assertEqual(len(mail.outbox), 2)
        prefix = settings.EMAIL_SUBJECT_PREFIX
        expected_subjects = {
            f'{prefix} New Cluster Access Request',
            (f'{prefix} New Project Request '
             f'({new_project_request.project.name}) Processed'),
        }
        for email in mail.outbox:
            subject = email.subject
            self.assertIn(subject, expected_subjects)
            expected_subjects.remove(subject)
        self.assertFalse(expected_subjects)

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
        if flag_enabled('BRC_ONLY'):
            computing_allowance_name = BRCAllowances.CO
        elif flag_enabled('LRC_ONLY'):
            computing_allowance_name = LRCAllowances.LR
        else:
            raise ImproperlyConfigured

        computing_allowance = Resource.objects.get(
            name=computing_allowance_name)
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
        # approval should not have been sent. In addition, an email about a new
        # cluster access request should have been sent.
        self.assertEqual(len(mail.outbox), 2)
        prefix = settings.EMAIL_SUBJECT_PREFIX
        expected_subjects = {
            f'{prefix} New Cluster Access Request',
            (f'{prefix} New Project Request '
             f'({new_project_request.project.name}) Processed'),
        }
        for email in mail.outbox:
            subject = email.subject
            self.assertIn(subject, expected_subjects)
            expected_subjects.remove(subject)
        self.assertFalse(expected_subjects)

        # The 'CLUSTER_NAME Compute' Allocation's Service Units should have
        # increased.
        self.service_units_attribute.refresh_from_db()
        self.assertGreater(
            Decimal(self.service_units_attribute.value),
            self.existing_service_units)

    def test_post_approves_and_processes_request_for_null_period_recharge(self):
        """Test that a POST request for a new project request (Recharge)
        with a null AllocationPeriod is both approved and processed."""
        if flag_enabled('BRC_ONLY'):
            computing_allowance_name = BRCAllowances.RECHARGE
        elif flag_enabled('LRC_ONLY'):
            computing_allowance_name = LRCAllowances.RECHARGE
        else:
            raise ImproperlyConfigured

        computing_allowance = Resource.objects.get(
            name=computing_allowance_name)
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
        # approval should not have been sent. In addition, an email about a new
        # cluster access request should have been sent.
        self.assertEqual(len(mail.outbox), 2)
        prefix = settings.EMAIL_SUBJECT_PREFIX
        expected_subjects = {
            f'{prefix} New Cluster Access Request',
            (f'{prefix} New Project Request '
             f'({new_project_request.project.name}) Processed'),
        }
        for email in mail.outbox:
            subject = email.subject
            self.assertIn(subject, expected_subjects)
            expected_subjects.remove(subject)
        self.assertFalse(expected_subjects)

        # The 'CLUSTER_NAME Compute' Allocation's Service Units should have
        # increased.
        self.service_units_attribute.refresh_from_db()
        self.assertGreater(
            Decimal(self.service_units_attribute.value),
            self.existing_service_units)

    # TODO
