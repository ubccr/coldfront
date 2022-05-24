from copy import deepcopy
from datetime import timedelta
from decimal import Decimal
from io import StringIO
from unittest.mock import patch
import re

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError

from coldfront.core.allocation.management.commands.start_allocation_period import Command as StartAllocationPeriodCommand
from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.allocation.models import AllocationRenewalRequestStatusChoice
from coldfront.core.allocation.models import AllocationStatusChoice
from coldfront.core.allocation.utils import prorated_allocation_amount
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectAllocationRequestStatusChoice
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.project.utils_.new_project_utils import SavioProjectApprovalRunner
from coldfront.core.project.utils_.new_project_utils import SavioProjectProcessingRunner
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period
from coldfront.core.project.utils_.renewal_utils import get_previous_allowance_year_period
from coldfront.core.project.utils_.renewal_utils import get_next_allowance_year_period
from coldfront.core.resource.models import Resource
from coldfront.core.utils.common import display_time_zone_current_date
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import TestBase


def no_op(*args, **kwargs):
    """Do nothing."""
    pass


def raise_exception(*args, **kwargs):
    """Raise an exception."""
    raise Exception('Test exception.')


class TestStartAllocationPeriod(TestBase):
    """A class for testing the start_allocation_period management
    command."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

        self.current_date = display_time_zone_current_date()

        self.previous_allowance_year = get_previous_allowance_year_period()
        self.current_allowance_year = get_current_allowance_year_period()
        self.next_allowance_year = get_next_allowance_year_period()

        self.previous_instructional_period = AllocationPeriod.objects.filter(
            end_date__lt=self.current_date).latest('end_date')
        # There are some dates not covered by instructional AllocationPeriods
        # on which these tests would fail, so create one.
        self.current_instructional_period = AllocationPeriod.objects.create(
            name='Instructional Period',
            start_date=self.current_date,
            end_date=self.current_date + timedelta(days=90))

        self.fca = SavioProjectAllocationRequest.FCA
        self.ica = SavioProjectAllocationRequest.ICA
        self.pca = SavioProjectAllocationRequest.PCA

        # Create existing FCA, ICA, and PCA projects, activated by new project
        # requests from previous AllocationPeriods.
        prefix_by_allocation_type = {
            self.fca: 'fc_',
            self.ica: 'ic_',
            self.pca: 'pc_',
        }
        previous_allocation_periods_by_allocation_type = {
            self.fca: self.previous_allowance_year,
            self.ica: self.previous_instructional_period,
            self.pca: self.previous_allowance_year,
        }
        num_service_units = Decimal('300000.00')
        projects_by_name = {}
        for allocation_type in previous_allocation_periods_by_allocation_type:
            prefix = prefix_by_allocation_type[allocation_type]
            allocation_period = previous_allocation_periods_by_allocation_type[
                allocation_type]
            name = f'{prefix}existing'
            projects_by_name[name] = self.create_project(
                name, allocation_type, allocation_period, num_service_units,
                approve=True, process=True)

        # Create an AllocationRenewalRequest for the FCA.
        fc_existing = Project.objects.get(name='fc_existing')
        AllocationRenewalRequest.objects.create(
            requester=User.objects.get(
                username=f'{fc_existing.name}_requester'),
            pi=User.objects.get(username=f'{fc_existing.name}_pi'),
            allocation_period=self.current_allowance_year,
            status=AllocationRenewalRequestStatusChoice.objects.get(
                name='Approved'),
            pre_project=fc_existing,
            post_project=fc_existing,
            num_service_units=num_service_units,
            request_time=utc_now_offset_aware(),
            approval_time=utc_now_offset_aware())

        # Create new project requests for new FCA, ICA, and PCA projects for
        # the current AllocationPeriod.
        current_allocation_periods_by_allocation_type = {
            self.fca: self.current_allowance_year,
            self.ica: self.current_instructional_period,
            self.pca: self.current_allowance_year,
        }
        for allocation_type in current_allocation_periods_by_allocation_type:
            prefix = prefix_by_allocation_type[allocation_type]
            allocation_period = current_allocation_periods_by_allocation_type[
                allocation_type]
            name = f'{prefix}new'
            projects_by_name[name] = self.create_project(
                name, allocation_type, allocation_period, num_service_units,
                approve=True, process=False)

    @staticmethod
    def call_command(allocation_period_id, skip_deactivations=False,
                     dry_run=False):
        """Call the command with the given AllocationPeriod ID and
        optional skip_deactivation and dry_run flags, returning the
        messages written to stdout and stderr."""
        out, err = StringIO(), StringIO()
        args = ['start_allocation_period', allocation_period_id]
        if skip_deactivations:
            args.append('--skip_deactivations')
        if dry_run:
            args.append('--dry_run')
        kwargs = {'stdout': out, 'stderr': err}
        call_command(*args, **kwargs)
        return out.getvalue(), err.getvalue()

    @staticmethod
    def create_project(name, allocation_type, allocation_period,
                       num_service_units, approve=False, process=False):
        """Create and return a Project with the given name, from a
        new project request with the given allocation type,
        AllocationPeriod, and number of service units. Optionally
        approve and/or process the request."""
        new_status = ProjectStatusChoice.objects.get(name='New')
        project = Project.objects.create(name=name, status=new_status)

        new_allocation_status = AllocationStatusChoice.objects.get(name='New')
        allocation = Allocation.objects.create(
            project=project, status=new_allocation_status)
        resource = Resource.objects.get(name='Savio Compute')
        allocation.resources.add(resource)
        allocation.save()

        requester = User.objects.create(
            username=f'{name}_requester', email=f'{name}_requester@email.com')
        pi = User.objects.create(
            username=f'{name}_pi', email=f'{name}_pi@email.com')

        approved_processing_request_status = \
            ProjectAllocationRequestStatusChoice.objects.get(
                name='Approved - Processing')
        new_project_request = SavioProjectAllocationRequest.objects.create(
            requester=requester,
            allocation_type=allocation_type,
            allocation_period=allocation_period,
            pi=pi,
            project=project,
            pool=False,
            survey_answers={},
            status=approved_processing_request_status,
            request_time=utc_now_offset_aware())

        # Allow runners to process requests with non-current periods.
        runner_args = (new_project_request, num_service_units)
        with patch.object(AllocationPeriod, 'assert_not_ended', no_op):
            with patch.object(AllocationPeriod, 'assert_started', no_op):
                # If process is True, approve first.
                if process or approve:
                    approval_runner = SavioProjectApprovalRunner(*runner_args)
                    approval_runner.run()
                new_project_request.refresh_from_db()
                if process:
                    processing_runner = SavioProjectProcessingRunner(
                        *runner_args)
                    processing_runner.run()

        project.refresh_from_db()
        return project

    def assert_new_project_request_to_process(self, expected_num_fcas=None,
                                              expected_num_icas=None,
                                              expected_num_pcas=None):
        """Assert that the number of new project requests to be
        processed are equal to the expected numbers. Return a mapping
        from request ID to the number of service units to be
        allocated.

        If an expected number is None, ignore requests of that type."""
        types_and_nums = [
            (self.fca, expected_num_fcas),
            (self.ica, expected_num_icas),
            (self.pca, expected_num_pcas),
        ]
        num_service_units_by_id = {}
        for allocation_type, expected_num in types_and_nums:
            if expected_num is None:
                continue
            requests = SavioProjectAllocationRequest.objects.filter(
                allocation_type=allocation_type,
                status__name='Approved - Scheduled')
            self.assertEqual(requests.count(), expected_num)
            for request in requests:
                num_service_units = getattr(
                    settings, f'{request.allocation_type}_DEFAULT_ALLOCATION')
                if allocation_type != self.ica:
                    num_service_units = prorated_allocation_amount(
                        num_service_units, utc_now_offset_aware(),
                        request.allocation_period)
                num_service_units_by_id[request.id] = num_service_units
        return num_service_units_by_id

    def assert_output(self, output, expected_num_lines, project_names_by_id,
                      num_sus_by_new_project_request_id,
                      num_sus_by_renewal_request_id, dry_run=False):
        """Assert that the given stdout output has exactly the expected
        number of lines, and that the Projects and requests included in
        the output are exactly the expected ones."""
        # Remove newlines and ANSI color codes from the output.
        output_lines = [
            line.strip()[7:] for line in output.split('\n') if line.strip()]
        self.assertEqual(expected_num_lines, len(output_lines))

        num_new_project_requests = len(num_sus_by_new_project_request_id)
        num_renewal_requests = len(num_sus_by_renewal_request_id)

        deactivation_prefix = 'Would deactivate' if dry_run else 'Deactivated'
        processing_prefix_template = (
            'Would process {0}' if dry_run else 'Processed {0}')
        new_project_request_processing_prefix = \
            processing_prefix_template.format(
                SavioProjectAllocationRequest.__name__)
        renewal_request_processing_prefix = processing_prefix_template.format(
            AllocationRenewalRequest.__name__)

        # Assert that each output message corresponds to an entity expected to
        # be there, with the expected associated contents. Remove each entity
        # from the respective dictionary.
        for line in output_lines:
            if line.startswith(deactivation_prefix):
                project_id, actual_project_name = \
                    self.extract_deactivation_message_entries(
                        line, dry_run=dry_run)
                project_id = int(project_id)
                expected_project_name = project_names_by_id.pop(
                    project_id, None)
                if expected_project_name is None:
                    self.fail(
                        f'Project {project_id} is unexpectedly marked for '
                        f'deactivation.')
                self.assertEqual(expected_project_name, actual_project_name)
            elif line.startswith(new_project_request_processing_prefix):
                request_id, num_service_units = \
                    self.extract_processing_message_entries(
                        line, SavioProjectAllocationRequest, dry_run=dry_run)
                request_id = int(request_id)
                num_service_units = Decimal(num_service_units)
                expected_num_service_units = \
                    num_sus_by_new_project_request_id.pop(request_id, None)
                if expected_num_service_units is None:
                    self.fail(
                        f'SavioProjectAllocationRequest {request_id} is '
                        f'unexpectedly marked for processing.')
                self.assertEqual(expected_num_service_units, num_service_units)
            elif line.startswith(renewal_request_processing_prefix):
                request_id, num_service_units = \
                    self.extract_processing_message_entries(
                        line, AllocationRenewalRequest, dry_run=dry_run)
                request_id = int(request_id)
                num_service_units = Decimal(num_service_units)
                expected_num_service_units = num_sus_by_renewal_request_id.pop(
                    request_id, None)
                if expected_num_service_units is None:
                    self.fail(
                        f'AllocationRenewalRequest {request_id} is '
                        f'unexpectedly marked for processing.')
                self.assertEqual(expected_num_service_units, num_service_units)
            elif not dry_run and 'successes' in line and 'failures' in line:
                if SavioProjectAllocationRequest.__name__ in line:
                    expected_line = (
                        f'Processed {num_new_project_requests} '
                        f'{SavioProjectAllocationRequest.__name__}s, with '
                        f'{num_new_project_requests} successes and 0 '
                        f'failures.')
                else:
                    expected_line = (
                        f'Processed {num_renewal_requests} '
                        f'{AllocationRenewalRequest.__name__}s, with '
                        f'{num_renewal_requests} successes and 0 failures.')
                self.assertIn(expected_line, line)
            else:
                self.fail(f'Encountered unexpected line: {line}')

        # Assert that each dictionary is empty, meaning that no expected
        # entities were not processed.
        self.assertFalse(project_names_by_id)
        self.assertFalse(num_sus_by_new_project_request_id)
        self.assertFalse(num_sus_by_renewal_request_id)

    def assert_projects_to_deactivate(self, expected_num_fcas=None,
                                      expected_num_icas=None,
                                      expected_num_pcas=None):
        """Assert that the numbers of Projects to be deactivated are
        equal to the expected numbers. Return a mapping from project ID
        to project name.

        If an expected number is None, ignore Projects of that type."""
        prefixes_and_nums = [
            ('fc_', expected_num_fcas),
            ('ic_', expected_num_icas),
            ('pc_', expected_num_pcas),
        ]
        project_names_by_id = {}
        for prefix, expected_num in prefixes_and_nums:
            if expected_num is None:
                continue
            projects = Project.objects.filter(
                name__startswith=prefix, status__name='Active')
            self.assertEqual(projects.count(), expected_num)
            for project in projects:
                project_names_by_id[project.id] = project.name
        return project_names_by_id

    def assert_renewal_requests_to_process(self, expected_num_fcas=None,
                                           expected_num_icas=None,
                                           expected_num_pcas=None):
        """Assert that the number of renewal requests to be processed
        are equal to the expected numbers. Return a mapping from request
        ID to the number of service units to be allocated.

        If an expected number is None, ignore requests of that type."""
        prefixes_and_nums = [
            ('fc_', expected_num_fcas),
            ('ic_', expected_num_icas),
            ('pc_', expected_num_pcas),
        ]
        types_by_prefix = {
            'fc_': self.fca,
            'ic_': self.ica,
            'pc_': self.pca,
        }
        num_service_units_by_id = {}
        for prefix, expected_num in prefixes_and_nums:
            if expected_num is None:
                continue
            requests = AllocationRenewalRequest.objects.filter(
                post_project__name__startswith=prefix, status__name='Approved')
            self.assertEqual(requests.count(), expected_num)
            for request in requests:
                num_service_units = getattr(
                    settings, f'{types_by_prefix[prefix]}_DEFAULT_ALLOCATION')
                if prefix != 'ic_':
                    num_service_units = prorated_allocation_amount(
                        num_service_units, utc_now_offset_aware(),
                        request.allocation_period)
                num_service_units_by_id[request.id] = num_service_units
        return num_service_units_by_id

    @staticmethod
    def extract_deactivation_message_entries(message, dry_run=False):
        """Given a line relating to Project deactivation, return the
        outputted Project ID and name."""
        pattern_template = (
            '{0} Project (?P<project_id>\d+) \((?P<project_name>[a-z0-9_]+)\) '
            'and reset Service Units\.')
        if dry_run:
            pattern = pattern_template.format('Would deactivate')
        else:
            pattern = pattern_template.format('Deactivated')
        return re.match(pattern, message).groups()

    @staticmethod
    def extract_processing_message_entries(message, model, dry_run=False):
        """Given a line relating to request processing, return the
        outputted request ID and number of service units."""
        pattern_template = (
            f'{{0}} {model.__name__} (?P<request_id>\d+) with '
            f'(?P<num_service_units>[0-9.]+) service units.')
        if dry_run:
            pattern = pattern_template.format('Would process')
        else:
            pattern = pattern_template.format('Processed')
        return re.match(pattern, message).groups()

    def test_allocation_period_nonexistent(self):
        """Test that an ID for a nonexistent AllocationPeriod raises an
        error."""
        _id = sum(AllocationPeriod.objects.values_list('id', flat=True))
        with self.assertRaises(CommandError) as cm:
            self.call_command(_id)
        self.assertIn('does not exist', str(cm.exception))

    def test_allocation_period_not_current(self):
        """Test that an ID for an AllocationPeriod whose start and end
        dates do not include the current date raises an error."""
        past_id = self.previous_allowance_year.id
        future_id = self.next_allowance_year.id
        for _id in (past_id, future_id):
            with self.assertRaises(CommandError) as cm:
                self.call_command(_id)
            self.assertIn('is not current', str(cm.exception))

    def test_failed_deactivations_preempt_processing(self):
        """Test that, if one or more Projects fail to be deactivated,
        request processing does not proceed."""

        def assert_outcome(_id, error_message):
            """Assert that the command raises an exception for the
            AllocationPeriod with the given ID, including the given
            error message, for both dry runs and non-dry runs."""
            path = (
                'coldfront.core.allocation.management.commands.'
                'start_allocation_period')
            dry_run_and_methods_to_patch = [
                (True, f'{path}.get_accounting_allocation_objects'),
                (False, f'{path}.deactivate_project_and_allocation'),
            ]
            for dry_run, method_to_patch in dry_run_and_methods_to_patch:
                with patch(method_to_patch) as patched_method:
                    patched_method.side_effect = raise_exception
                    with self.assertRaises(CommandError) as cm:
                        self.call_command(_id, dry_run=dry_run)
                    self.assertEqual(error_message, str(cm.exception))

        # Retrieve the numbers of deactivated Projects and complete requests.
        num_deactivated_projects = Project.objects.filter(
            status__name='Inactive').count()
        num_complete_new_project_requests = \
            SavioProjectAllocationRequest.objects.filter(
                status__name='Approved - Complete').count()
        num_complete_renewal_requests = \
            AllocationRenewalRequest.objects.filter(
                status__name='Complete').count()

        assert_outcome(
            self.current_allowance_year.id,
            'Failed to deactivate 1/1 FCA Projects and 1/1 PCA Projects.')
        assert_outcome(
            self.current_instructional_period.id,
            'Failed to deactivate 1/1 ICA Projects.')

        # The numbers of deactivated Projects and complete requests should not
        # have increased.
        self.assertEqual(
            num_deactivated_projects,
            Project.objects.filter(status__name='Inactive').count())
        self.assertEqual(
            num_complete_new_project_requests,
            SavioProjectAllocationRequest.objects.filter(
                status__name='Approved - Complete').count())
        self.assertEqual(
            num_complete_renewal_requests,
            AllocationRenewalRequest.objects.filter(
                status__name='Complete').count())

    def test_multiple_runs_avoid_redundant_work(self):
        """Test that running the command multiple times does not
        re-deactivate Projects or re-process already completed
        requests."""
        allocation_period_id = self.current_allowance_year.id

        # Run the command the first time,
        output, error = self.call_command(allocation_period_id, dry_run=False)
        self.assertTrue(output)
        self.assertFalse(error)

        fc_existing = Project.objects.get(name='fc_existing')
        fc_existing_str = (
            f'Deactivated Project {fc_existing.id} ({fc_existing.name})')
        self.assertIn(fc_existing_str, output)

        pc_existing = Project.objects.get(name='pc_existing')
        pc_existing_str = (
            f'Deactivated Project {pc_existing.id} ({pc_existing.name})')
        self.assertIn(pc_existing_str, output)

        fc_new_request = SavioProjectAllocationRequest.objects.get(
            project=Project.objects.get(name='fc_new'))
        fc_new_request_str = (
            f'Processed SavioProjectAllocationRequest {fc_new_request.id}')
        self.assertIn(fc_new_request_str, output)

        pc_new_request = SavioProjectAllocationRequest.objects.get(
            project=Project.objects.get(name='pc_new'))
        pc_new_request_str = (
            f'Processed SavioProjectAllocationRequest {pc_new_request.id}')
        self.assertIn(pc_new_request_str, output)

        fc_renewal_request = AllocationRenewalRequest.objects.get(
            post_project=fc_existing)
        fc_renewal_request_str = (
            f'Processed AllocationRenewalRequest {fc_renewal_request.id}')
        self.assertIn(fc_renewal_request_str, output)

        # The Projects should not appear in a subsequent run because their end
        # dates are no longer less than the start date of the AllocationPeriod.
        # The requests should not appear because they are in a completed state.
        output, error = self.call_command(allocation_period_id, dry_run=False)
        self.assertNotIn('Deactivated', output)
        self.assertNotIn(fc_existing_str, output)
        self.assertNotIn(pc_existing_str, output)
        self.assertNotIn(fc_new_request_str, output)
        self.assertNotIn(pc_new_request_str, output)
        self.assertNotIn(fc_renewal_request_str, output)
        self.assertIn('Processed 0 SavioProjectAllocationRequests', output)
        self.assertIn('Processed 0 AllocationRenewalRequests', output)
        self.assertFalse(error)

    def test_output_for_allowance_year_period(self):
        """Test that the messages written to stdout and stderr are
        exactly the ones expected for an AllocationPeriod representing
        an allowance year, with and without the dry_run flag."""
        allocation_period_id = self.current_allowance_year.id

        kwargs = {'expected_num_fcas': 1, 'expected_num_pcas': 1}
        # One FCA Project and one PCA Project should be deactivated.
        project_names_by_id = self.assert_projects_to_deactivate(**kwargs)
        # One FCA new project request and one PCA new project request should be
        # processed.
        num_sus_by_new_project_request_id = \
            self.assert_new_project_request_to_process(**kwargs)
        # One FCA renewal request should be processed.
        num_sus_by_renewal_request_id = \
            self.assert_renewal_requests_to_process(expected_num_fcas=1)
        # There should be 5 entities.
        expected_num_entities = (len(project_names_by_id) +
                                 len(num_sus_by_new_project_request_id) +
                                 len(num_sus_by_renewal_request_id))
        self.assertEqual(expected_num_entities, 5)

        for dry_run in (True, False):
            output, error = self.call_command(
                allocation_period_id, dry_run=dry_run)
            self.assertTrue(output)
            self.assertFalse(error)
            # When dry_run is False, there should be two more lines of output.
            self.assert_output(
                output, expected_num_entities + 2 * int(not dry_run),
                deepcopy(project_names_by_id),
                deepcopy(num_sus_by_new_project_request_id),
                deepcopy(num_sus_by_renewal_request_id), dry_run=dry_run)

    def test_output_for_instructional_period(self):
        """Test that the messages written to stdout and stderr are
        exactly the ones expected for an AllocationPeriod representing
        an instructional period, with and without the dry_run flag."""
        allocation_period_id = self.current_instructional_period.id

        kwargs = {'expected_num_icas': 1}
        # One ICA Project should be deactivated.
        project_names_by_id = self.assert_projects_to_deactivate(**kwargs)
        # One ICA new project request should be processed.
        num_sus_by_new_project_request_id = \
            self.assert_new_project_request_to_process(**kwargs)
        # Zero ICA renewal requests should be processed.
        num_sus_by_renewal_request_id = \
            self.assert_renewal_requests_to_process()
        # There should be 2 entities.
        expected_num_entities = (len(project_names_by_id) +
                                 len(num_sus_by_new_project_request_id) +
                                 len(num_sus_by_renewal_request_id))
        self.assertEqual(expected_num_entities, 2)

        for dry_run in (True, False):
            output, error = self.call_command(
                allocation_period_id, dry_run=dry_run)
            self.assertTrue(output)
            self.assertFalse(error)
            # When dry_run is False, there should be two more lines of output.
            self.assert_output(
                output, expected_num_entities + 2 * int(not dry_run),
                deepcopy(project_names_by_id),
                deepcopy(num_sus_by_new_project_request_id),
                deepcopy(num_sus_by_renewal_request_id), dry_run=dry_run)

    def test_skip_deactivations_flag(self):
        """Test that deactivations are not run if the skip_deactivations
        flag is provided."""
        allocation_period_id = self.current_allowance_year.id

        dry_run = True

        output, error = self.call_command(
            allocation_period_id, skip_deactivations=False, dry_run=dry_run)
        self.assertIn('Would deactivate', output)
        self.assertFalse(error)

        output, error = self.call_command(
            allocation_period_id, skip_deactivations=True, dry_run=dry_run)
        self.assertNotIn('Would deactivate', output)
        self.assertFalse(error)

        # Raise an exception during deactivation so that processing is avoided
        # on the first run.
        dry_run = False
        with patch.object(
                StartAllocationPeriodCommand, 'deactivate_projects',
                raise_exception):
            with self.assertRaises(Exception):
                self.call_command(
                    allocation_period_id, skip_deactivations=False,
                    dry_run=dry_run)

            output, error = self.call_command(
                allocation_period_id, skip_deactivations=True, dry_run=dry_run)
            self.assertNotIn('Deactivated', output)
            self.assertFalse(error)
