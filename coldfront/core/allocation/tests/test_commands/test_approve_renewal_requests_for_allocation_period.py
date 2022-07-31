from datetime import timedelta
from decimal import Decimal
from io import StringIO
import iso8601

from django.contrib.auth.models import User
from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError

from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.allocation.models import AllocationRenewalRequestStatusChoice
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period
from coldfront.core.project.utils_.renewal_utils import get_next_allowance_year_period
from coldfront.core.resource.models import Resource
from coldfront.core.resource.utils_.allowance_utils.constants import BRCAllowances
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.utils.common import display_time_zone_current_date
from coldfront.core.utils.common import display_time_zone_date_to_utc_datetime
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import TestBase


class TestApproveRenewalRequestsForAllocationPeriod(TestBase):
    """A class for testing the
    approve_renewal_requests_for_allocation_period management
    command."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        computing_allowance = Resource.objects.get(name=BRCAllowances.FCA)
        self.num_service_units = Decimal(
            ComputingAllowanceInterface().service_units_from_name(
                computing_allowance.name))

    @staticmethod
    def call_command(allocation_period_id, dry_run=False):
        """Call the command with the given AllocationPeriod ID and
        optional dry_run flag, returning the messages written to stdout
        and stderr."""
        out, err = StringIO(), StringIO()
        args = [
            'approve_renewal_requests_for_allocation_period',
            allocation_period_id]
        if dry_run:
            args.append('--dry_run')
        kwargs = {'stdout': out, 'stderr': err}
        call_command(*args, **kwargs)
        return out.getvalue(), err.getvalue()

    @staticmethod
    def create_request_and_supporting_objects(allocation_period):
        """Create and return an AllocationRenewalRequest, a Project, a
        requester, and a PI, under the given AllocationPeriod."""
        project_name = 'fc_project'
        active_project_status = ProjectStatusChoice.objects.get(name='Active')
        project = Project.objects.create(
            name=project_name,
            title=project_name,
            status=active_project_status)
        requester = User.objects.create(
            email='requester@email.com',
            first_name='Requester',
            last_name='User',
            username='requester')
        pi = User.objects.create(
            email='pi@email.com',
            first_name='PI',
            last_name='User',
            username='pi')
        allocation_period_start_utc = display_time_zone_date_to_utc_datetime(
            allocation_period.start_date)
        request = AllocationRenewalRequest.objects.create(
            requester=requester,
            pi=pi,
            computing_allowance=Resource.objects.get(name=BRCAllowances.FCA),
            allocation_period=allocation_period,
            status=AllocationRenewalRequestStatusChoice.objects.get(
                name='Under Review'),
            pre_project=project,
            post_project=project,
            request_time=allocation_period_start_utc - timedelta(days=1))
        return request, project, requester, pi

    def test_allocation_period_nonexistent(self):
        """Test that an ID for a nonexistent AllocationPeriod raises an
        error."""
        _id = sum(AllocationPeriod.objects.values_list('id', flat=True))
        with self.assertRaises(CommandError) as cm:
            self.call_command(_id)
        self.assertIn('does not exist', str(cm.exception))

    def test_allocation_period_not_allowance_year(self):
        """Test that an Allocation Period that does not represent an
        allowance year raises an error."""
        _id = AllocationPeriod.objects.exclude(
            name__startswith='Allowance Year').first().id
        with self.assertRaises(CommandError) as cm:
            self.call_command(_id)
        self.assertIn(
            'does not represent an allowance year', str(cm.exception))

    def test_allocation_period_already_started(self):
        """Test that an AllocationPeriod that has already started raises
        an error."""
        current_date = display_time_zone_current_date()
        _id = AllocationPeriod.objects.filter(
            start_date__lt=current_date).first().id
        with self.assertRaises(CommandError) as cm:
            self.call_command(_id)
        self.assertIn('has already started', str(cm.exception))

    def test_requests_limited_by_conditions(self):
        """Test that a request is only considered if it meets the
        following conditions: its status is 'Under Review', its
        post_project is an FCA, its allocation_period is the given one,
        and its request_time is before the start_date of the period."""
        # A condition-meeting request should be included.
        allocation_period = get_next_allowance_year_period()
        _id = allocation_period.id
        request, _, _, _ = self.create_request_and_supporting_objects(
            allocation_period)
        output, error = self.call_command(_id, dry_run=True)
        expected_message = (
            f'Would automatically approve AllocationRenewalRequest '
            f'{request.id} for PI {request.pi}, scheduling '
            f'{self.num_service_units} to be granted to '
            f'{request.post_project.name} on {allocation_period.start_date}, '
            f'and emailing the requester and/or PI.')
        self.assertIn(expected_message, output)
        self.assertFalse(error)

        # A request failing to meet all conditions should not be included.

        # Non-'Under Review' status
        tmp_status = request.status
        for status in AllocationRenewalRequestStatusChoice.objects.exclude(
                name='Under Review'):
            request.status = status
            request.save()
            self.assertFalse(any(self.call_command(_id, dry_run=True)))
        request.status = tmp_status
        request.save()

        output, error = self.call_command(_id, dry_run=True)
        self.assertIn(expected_message, output)
        self.assertFalse(error)

        # Non-FCA/PCA project
        project = request.post_project
        tmp_project_name = project.name
        tmp_computing_allowance = request.computing_allowance
        computing_allowance_interface = ComputingAllowanceInterface()
        allowance_names = (
            BRCAllowances.CO,
            BRCAllowances.ICA,
            BRCAllowances.PCA,
            BRCAllowances.RECHARGE,
        )
        for allowance_name in allowance_names:
            prefix = computing_allowance_interface.code_from_name(
                allowance_name)
            project.name = prefix + project.name[3:]
            project.save()
            request.computing_allowance = Resource.objects.get(
                name=allowance_name)
            request.save()
            output, error = self.call_command(_id, dry_run=True)
            if allowance_name == BRCAllowances.PCA:
                self.assertTrue(output)
                self.assertFalse(error)
            else:
                self.assertFalse(output or error)
        project.name = tmp_project_name
        project.save()
        request.computing_allowance = tmp_computing_allowance
        request.save()

        output, error = self.call_command(_id, dry_run=True)
        self.assertIn(expected_message, output)
        self.assertFalse(error)

        # Different AllocationPeriod
        tmp_allocation_period = request.allocation_period
        request.allocation_period = get_current_allowance_year_period()
        request.save()
        self.assertFalse(any(self.call_command(_id, dry_run=True)))
        request.allocation_period = tmp_allocation_period
        request.save()

        output, error = self.call_command(_id, dry_run=True)
        self.assertIn(expected_message, output)
        self.assertFalse(error)

        # Late request time
        tmp_request_time = request.request_time
        request.request_time = display_time_zone_date_to_utc_datetime(
            allocation_period.start_date)
        request.save()
        self.assertFalse(any(self.call_command(_id, dry_run=True)))
        request.request_time = tmp_request_time
        request.save()

        output, error = self.call_command(_id, dry_run=True)
        self.assertIn(expected_message, output)
        self.assertFalse(error)

    def test_sends_emails(self):
        """Test that the command sends emails to the requester and/or
        the PI of the request."""
        allocation_period = get_next_allowance_year_period()
        _id = allocation_period.id
        request, _, _, _ = self.create_request_and_supporting_objects(
            allocation_period)

        self.assertEqual(len(mail.outbox), 0)

        # If the dry_run flag is provided, no email should be sent.
        output, error = self.call_command(_id, dry_run=True)
        self.assertTrue(output)
        self.assertFalse(error)

        self.assertEqual(len(mail.outbox), 0)

        # Otherwise, an email should be sent.
        output, error = self.call_command(_id, dry_run=False)
        self.assertTrue(output)
        self.assertFalse(error)

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        # The other email details are tested in the approval runner tests.
        expected_to = sorted([request.requester.email, request.pi.email])
        self.assertEqual(expected_to, sorted(email.to))

    def test_updates_request_fields(self):
        """Test that the command updates the request's state, status,
        and approval_time fields."""
        allocation_period = get_next_allowance_year_period()
        _id = allocation_period.id
        request, _, _, _ = self.create_request_and_supporting_objects(
            allocation_period)

        eligibility = request.state['eligibility']
        self.assertEqual(eligibility['status'], 'Pending')
        self.assertFalse(eligibility['timestamp'])
        self.assertEqual(request.status.name, 'Under Review')
        self.assertIsNone(request.approval_time)

        expected_message_template = (
            f'{{0}} AllocationRenewalRequest {request.id} for PI '
            f'{request.pi}, scheduling {self.num_service_units} to be granted '
            f'to {request.post_project.name} on '
            f'{allocation_period.start_date}, and emailing the requester '
            f'and/or PI.')

        # If the dry_run flag is provided, no update should occur.
        output, error = self.call_command(_id, dry_run=True)
        expected_message = expected_message_template.format(
            'Would automatically approve')
        self.assertIn(expected_message, output)
        self.assertFalse(error)

        request.refresh_from_db()
        eligibility = request.state['eligibility']
        self.assertEqual(eligibility['status'], 'Pending')
        self.assertFalse(eligibility['timestamp'])
        self.assertEqual(request.status.name, 'Under Review')
        self.assertIsNone(request.approval_time)

        # Otherwise, an update should occur.
        pre_time = utc_now_offset_aware()
        output, error = self.call_command(_id, dry_run=False)
        expected_message = expected_message_template.format(
            'Automatically approved')
        post_time = utc_now_offset_aware()
        self.assertIn(expected_message, output)
        self.assertFalse(error)

        request.refresh_from_db()
        eligibility = request.state['eligibility']
        self.assertEqual(eligibility['status'], 'Approved')
        timestamp_dt = iso8601.parse_date(eligibility['timestamp'])
        self.assertEqual(request.status.name, 'Approved')
        approval_time = request.approval_time
        self.assertTrue(pre_time <= timestamp_dt <= approval_time <= post_time)
