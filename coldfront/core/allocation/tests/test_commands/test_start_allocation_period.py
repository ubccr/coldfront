from copy import deepcopy
from datetime import timedelta
from decimal import Decimal
from io import StringIO
from unittest.mock import patch
import re
import random

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError

from coldfront.api.statistics.utils import get_accounting_allocation_objects
from coldfront.core.allocation.management.commands.start_allocation_period import Command as StartAllocationPeriodCommand
from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.allocation.models import AllocationRenewalRequestStatusChoice
from coldfront.core.allocation.models import AllocationStatusChoice
from coldfront.core.allocation.models import AllocationUser
from coldfront.core.allocation.models import AllocationUserAttribute
from coldfront.core.allocation.models import AllocationUserAttributeUsage
from coldfront.core.allocation.models import AllocationUserStatusChoice
from coldfront.core.allocation.utils import prorated_allocation_amount
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectAllocationRequestStatusChoice
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
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
        self.allowances_by_allocation_type = {
            self.fca: settings.FCA_DEFAULT_ALLOCATION,
            self.ica: settings.ICA_DEFAULT_ALLOCATION,
            self.pca: settings.PCA_DEFAULT_ALLOCATION,
        }
        self.usages_by_allocation_type = {
            _type: self.allowances_by_allocation_type[_type] - Decimal('0.01')
            for _type in self.allowances_by_allocation_type}
        projects_by_name = {}
        self.project_user_data_by_name = {}
        num_extra_users_per_project = 5
        for allocation_type in previous_allocation_periods_by_allocation_type:
            prefix = prefix_by_allocation_type[allocation_type]
            allowance = self.allowances_by_allocation_type[
                allocation_type]
            usage = self.usages_by_allocation_type[allocation_type]
            allocation_period = previous_allocation_periods_by_allocation_type[
                allocation_type]
            name = f'{prefix}existing'
            project = self.create_project(
                name, allocation_type, allocation_period, allowance,
                approve=True, process=True)
            self.set_project_usage(project, usage)
            projects_by_name[name] = project
            self.project_user_data_by_name[name] = self.create_project_users(
                project, num_extra_users_per_project)

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
            num_service_units=self.allowances_by_allocation_type[self.fca],
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
            num_service_units = prorated_allocation_amount(
                self.allowances_by_allocation_type[allocation_type],
                utc_now_offset_aware(), allocation_period)
            allocation_period = current_allocation_periods_by_allocation_type[
                allocation_type]
            name = f'{prefix}new'
            projects_by_name[name] = self.create_project(
                name, allocation_type, allocation_period, num_service_units,
                approve=True, process=False)

    def assert_existing_project_pre_state(self, allocation_period, project):
        """Assert that the given existing Project is 'Active', and that
        Allocation-related objects have the expected values."""
        active_project_status = ProjectStatusChoice.objects.get(name='Active')
        active_allocation_status = AllocationStatusChoice.objects.get(
            name='Active')

        self.assertEqual(project.status, active_project_status)

        objects = get_accounting_allocation_objects(project)
        allocation = objects.allocation
        self.assertEqual(allocation.status, active_allocation_status)
        self.assertEqual(allocation.start_date, self.current_date)
        self.assertEqual(allocation.end_date, allocation_period.end_date)

        if project.name.startswith('fc_'):
            allocation_type = self.fca
        elif project.name.startswith('ic_'):
            allocation_type = self.ica
        else:
            allocation_type = self.pca

        pre_allocation_allowance = self.allowances_by_allocation_type[
            allocation_type]
        allocation_attribute = objects.allocation_attribute
        self.assertEqual(
            Decimal(allocation_attribute.value), pre_allocation_allowance)

        pre_allocation_usage = self.usages_by_allocation_type[allocation_type]
        allocation_attribute_usage = objects.allocation_attribute_usage
        self.assertEqual(
            Decimal(allocation_attribute_usage.value), pre_allocation_usage)

    def assert_last_k_historical_values(self, obj, attr, pairs, pre_t, post_t):
        """Assert that the last k number of values for the attribute of
        the given object are equal to the given, where k is the number
        of given values.

        The values are pairs of the form (value, is_after_processing),
        where the latter denotes whether the historical object is after
        the call to the command. If not, its date should be before the
        processing time; otherwise, its date should be between the start
        and end times of processing."""
        historical_objs = list(obj.history.order_by('-history_date'))
        for i, pair in enumerate(pairs):
            value, is_after_processing = pair
            historical_obj = historical_objs[i]
            self.assertEqual(getattr(historical_obj, attr), value)
            history_date = historical_obj.history_date
            if not is_after_processing:
                self.assertLess(history_date, pre_t)
            else:
                self.assertTrue(pre_t < history_date < post_t)

    def assert_multiple_last_k_historical_values(self, data, pre_t, post_t):
        """Assert that the last k number of values for various objects
        are equal to the given.

        'data' is a list of tuples of the form (obj, attr, pairs)
        (inputs to assert_last_k_historical_values)."""
        for obj, attr, pairs in data:
            self.assert_last_k_historical_values(
                obj, attr, pairs, pre_t, post_t)

    def assert_new_project_pre_state(self, project):
        """Assert that the given new Project is 'New' and that it has no
        'Active' Allocation."""
        new_project_status = ProjectStatusChoice.objects.get(name='New')
        self.assertEqual(project.status, new_project_status)
        try:
            get_accounting_allocation_objects(project)
        except Allocation.DoesNotExist:
            pass
        else:
            self.fail(f'Project {project} should have no active Allocation.')

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

    def assert_post_state_activated(self, project, pre_time, post_time):
        """Assert that the given Project was activated between pre_time
        and post_time."""
        active_project_status = ProjectStatusChoice.objects.get(name='Active')
        new_project_status = ProjectStatusChoice.objects.get(name='New')
        active_allocation_status = AllocationStatusChoice.objects.get(
            name='Active')
        new_allocation_status = AllocationStatusChoice.objects.get(name='New')

        if project.name.startswith('fc_'):
            allocation_period = self.current_allowance_year
            allocation_type = self.fca
        elif project.name.startswith('ic_'):
            allocation_period = self.current_instructional_period
            allocation_type = self.ica
        else:
            allocation_period = self.current_allowance_year
            allocation_type = self.pca

        zero = Decimal('0.00')

        objects = get_accounting_allocation_objects(project)

        allocation = objects.allocation
        allocation_attribute = objects.allocation_attribute
        allocation_attribute_usage = objects.allocation_attribute_usage

        latest_project_statuses = (
            (active_project_status, True),
            (new_project_status, False))
        self.assert_last_k_historical_values(
            project, 'status', latest_project_statuses, pre_time,
            post_time)

        latest_allocation_statuses = (
            (active_allocation_status, True),
            (new_allocation_status, False))
        self.assert_last_k_historical_values(
            allocation, 'status', latest_allocation_statuses, pre_time,
            post_time)

        latest_allocation_start_dates = (
            (self.current_date, True),
            (None, False))
        self.assert_last_k_historical_values(
            allocation, 'start_date', latest_allocation_start_dates, pre_time,
            post_time)

        latest_allocation_end_dates = (
            (allocation_period.end_date, True),
            (None, False))
        self.assert_last_k_historical_values(
            allocation, 'end_date', latest_allocation_end_dates, pre_time,
            post_time)

        post_allocation_allowance = prorated_allocation_amount(
            self.allowances_by_allocation_type[allocation_type],
            utc_now_offset_aware(), allocation_period)
        latest_allocation_attribute_values = (
            (str(post_allocation_allowance), True),
            ('', True))
        self.assert_last_k_historical_values(
            allocation_attribute, 'value', latest_allocation_attribute_values,
            pre_time, post_time)

        latest_allocation_attribute_usage_values = (
            (zero, True),)
        self.assert_last_k_historical_values(
            allocation_attribute_usage, 'value',
            latest_allocation_attribute_usage_values, pre_time, post_time)

    def assert_post_state_deactivated(self, project, pre_time, post_time):
        """Assert that the given Project was deactivated between
        pre_time and post_time."""
        active_project_status = ProjectStatusChoice.objects.get(name='Active')
        inactive_project_status = ProjectStatusChoice.objects.get(
            name='Inactive')
        active_allocation_status = AllocationStatusChoice.objects.get(
            name='Active')
        expired_allocation_status = AllocationStatusChoice.objects.get(
            name='Expired')

        if project.name.startswith('fc_'):
            allocation_period = self.current_allowance_year
            prev_allocation_period = self.previous_allowance_year
            allocation_type = self.fca
        elif project.name.startswith('ic_'):
            allocation_period = self.current_instructional_period
            prev_allocation_period = self.previous_instructional_period
            allocation_type = self.ica
        else:
            allocation_period = self.current_allowance_year
            prev_allocation_period = self.previous_allowance_year
            allocation_type = self.pca

        zero = Decimal('0.00')

        objects = get_accounting_allocation_objects(
            project, enforce_allocation_active=False)

        pre_allocation_allowance = self.allowances_by_allocation_type[
            allocation_type]
        pre_allocation_usage = self.usages_by_allocation_type[allocation_type]

        allocation = objects.allocation
        allocation_attribute = objects.allocation_attribute
        allocation_attribute_usage = objects.allocation_attribute_usage

        latest_project_statuses = (
            (inactive_project_status, True),
            (active_project_status, False))
        self.assert_last_k_historical_values(
            project, 'status', latest_project_statuses, pre_time,
            post_time)

        latest_allocation_statuses = (
            (expired_allocation_status, True),
            (active_allocation_status, False))
        self.assert_last_k_historical_values(
            allocation, 'status', latest_allocation_statuses, pre_time,
            post_time)

        latest_allocation_start_dates = (
            (self.current_date, True),
            (self.current_date, False))
        self.assert_last_k_historical_values(
            allocation, 'start_date', latest_allocation_start_dates, pre_time,
            post_time)

        latest_allocation_end_dates = (
            (None, True),
            (prev_allocation_period.end_date, False))
        self.assert_last_k_historical_values(
            allocation, 'end_date', latest_allocation_end_dates, pre_time,
            post_time)

        post_allocation_allowance = prorated_allocation_amount(
            self.allowances_by_allocation_type[allocation_type],
            utc_now_offset_aware(), allocation_period)
        latest_allocation_attribute_values = (
            (str(zero), True),
            (str(pre_allocation_allowance), False))
        self.assert_last_k_historical_values(
            allocation_attribute, 'value', latest_allocation_attribute_values,
            pre_time, post_time)

        latest_allocation_attribute_usage_values = (
            (zero, True),
            (pre_allocation_usage, False))
        self.assert_last_k_historical_values(
            allocation_attribute_usage, 'value',
            latest_allocation_attribute_usage_values, pre_time, post_time)

        project_user_data = self.project_user_data_by_name[project.name]
        allocation_users = allocation.allocationuser_set.exclude(
            user__username__in=[
                f'{project.name}_requester', f'{project}_pi'])
        self.assertEqual(allocation_users.count(), len(project_user_data))
        for allocation_user in allocation_users:
            user = allocation_user.user
            self.assertIn(user.username, project_user_data)
            pre_allowance, pre_usage = project_user_data[user.username]
            post_allowance, post_usage = post_allocation_allowance, zero

            allocation_user_attribute = \
                allocation_user.allocationuserattribute_set.filter(
                    allocation_attribute_type__name='Service Units').first()
            latest_allocation_user_allowance_values = (
                (str(zero), True),
                (str(pre_allowance), False))
            self.assert_last_k_historical_values(
                allocation_user_attribute, 'value',
                latest_allocation_user_allowance_values, pre_time, post_time)

            allocation_user_attribute_usage = \
                allocation_user_attribute.allocationuserattributeusage
            latest_allocation_user_usage_values = (
                (post_usage, True),
                (pre_usage, False))
            self.assert_last_k_historical_values(
                allocation_user_attribute_usage, 'value',
                latest_allocation_user_usage_values, pre_time, post_time)

    def assert_post_state_deactivated_renewed(self, project, pre_time,
                                              post_time):
        """Assert that the given Project was deactivated and renewed
        between pre_time and post_time."""
        active_project_status = ProjectStatusChoice.objects.get(name='Active')
        inactive_project_status = ProjectStatusChoice.objects.get(
            name='Inactive')
        active_allocation_status = AllocationStatusChoice.objects.get(
            name='Active')
        expired_allocation_status = AllocationStatusChoice.objects.get(
            name='Expired')

        if project.name.startswith('fc_'):
            allocation_period = self.current_allowance_year
            prev_allocation_period = self.previous_allowance_year
            allocation_type = self.fca
        elif project.name.startswith('ic_'):
            allocation_period = self.current_instructional_period
            prev_allocation_period = self.previous_instructional_period
            allocation_type = self.ica
        else:
            allocation_period = self.current_allowance_year
            prev_allocation_period = self.previous_allowance_year
            allocation_type = self.pca

        zero = Decimal('0.00')

        objects = get_accounting_allocation_objects(project)

        pre_allocation_allowance = self.allowances_by_allocation_type[
            allocation_type]
        pre_allocation_usage = self.usages_by_allocation_type[allocation_type]

        allocation = objects.allocation
        allocation_attribute = objects.allocation_attribute
        allocation_attribute_usage = objects.allocation_attribute_usage

        latest_project_statuses = (
            (active_project_status, True),
            (inactive_project_status, True),
            (active_project_status, False))
        self.assert_last_k_historical_values(
            project, 'status', latest_project_statuses, pre_time,
            post_time)

        latest_allocation_statuses = (
            (active_allocation_status, True),
            (expired_allocation_status, True),
            (active_allocation_status, False))
        self.assert_last_k_historical_values(
            allocation, 'status', latest_allocation_statuses, pre_time,
            post_time)

        latest_allocation_start_dates = (
            (self.current_date, True),
            (self.current_date, True),
            (self.current_date, False))
        self.assert_last_k_historical_values(
            allocation, 'start_date', latest_allocation_start_dates, pre_time,
            post_time)

        latest_allocation_end_dates = (
            (allocation_period.end_date, True),
            (None, True),
            (prev_allocation_period.end_date, False))
        self.assert_last_k_historical_values(
            allocation, 'end_date', latest_allocation_end_dates, pre_time,
            post_time)

        post_allocation_allowance = prorated_allocation_amount(
            self.allowances_by_allocation_type[allocation_type],
            utc_now_offset_aware(), allocation_period)
        latest_allocation_attribute_values = (
            (str(post_allocation_allowance), True),
            (str(zero), True),
            (str(pre_allocation_allowance), False))
        self.assert_last_k_historical_values(
            allocation_attribute, 'value', latest_allocation_attribute_values,
            pre_time, post_time)

        latest_allocation_attribute_usage_values = (
            (zero, True),
            (pre_allocation_usage, False))
        self.assert_last_k_historical_values(
            allocation_attribute_usage, 'value',
            latest_allocation_attribute_usage_values, pre_time, post_time)

        project_user_data = self.project_user_data_by_name[project.name]
        allocation_users = allocation.allocationuser_set.exclude(
            user__username__in=[
                f'{project.name}_requester', f'{project}_pi'])
        self.assertEqual(allocation_users.count(), len(project_user_data))
        for allocation_user in allocation_users:
            user = allocation_user.user
            self.assertIn(user.username, project_user_data)
            pre_allowance, pre_usage = project_user_data[user.username]
            post_allowance, post_usage = post_allocation_allowance, zero

            allocation_user_attribute = \
                allocation_user.allocationuserattribute_set.filter(
                    allocation_attribute_type__name='Service Units').first()
            latest_allocation_user_allowance_values = (
                (str(post_allowance), True),
                (str(zero), True),
                (str(pre_allowance), False))
            self.assert_last_k_historical_values(
                allocation_user_attribute, 'value',
                latest_allocation_user_allowance_values, pre_time, post_time)

            allocation_user_attribute_usage = \
                allocation_user_attribute.allocationuserattributeusage
            latest_allocation_user_usage_values = (
                (post_usage, True),
                (pre_usage, False))
            self.assert_last_k_historical_values(
                allocation_user_attribute_usage, 'value',
                latest_allocation_user_usage_values, pre_time, post_time)

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

    @staticmethod
    def create_project_users(project, k):
        """Given a Project, create k ProjectUsers under it, with random
        Service Units allowances and usages. Return a mapping from
        username object to (allowance, usage)."""
        objects = get_accounting_allocation_objects(project)
        allocation = objects.allocation
        allocation_allowance = Decimal(objects.allocation_attribute.value)

        project_user_kwargs = {
            'role': ProjectUserRoleChoice.objects.get(name='User'),
            'status': ProjectUserStatusChoice.objects.get(name='Active'),
        }
        active_allocation_status = AllocationUserStatusChoice.objects.get(
            name='Active')
        service_units_type = AllocationAttributeType.objects.get(
            name='Service Units')

        service_units_by_username = {}
        for i in range(k):
            username = f'{project.name}_user_{i}'
            user = User.objects.create(
                username=username, email=f'{username}@email.com')
            ProjectUser.objects.create(
                project=project, user=user, **project_user_kwargs)
            allocation_user = AllocationUser.objects.create(
                allocation=allocation, user=user,
                status=active_allocation_status)
            allocation_user_allowance = Decimal(
                random.randint(1, allocation_allowance))
            allocation_user_attribute = AllocationUserAttribute.objects.create(
                allocation_attribute_type=service_units_type,
                allocation=allocation,
                allocation_user=allocation_user,
                value=str(allocation_user_allowance))

            allocation_user_usage = Decimal(
                random.randint(1, allocation_user_allowance))
            allocation_user_attribute_usage = \
                allocation_user_attribute.allocationuserattributeusage
            allocation_user_attribute_usage.value = allocation_user_usage
            allocation_user_attribute_usage.save()

            service_units_by_username[username] = (
                allocation_user_allowance, allocation_user_usage)

        return service_units_by_username

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

    @staticmethod
    def set_project_usage(project, value):
        """Set the Service Units usage for the given Project to the
        given value."""
        objects = get_accounting_allocation_objects(project)
        usage = objects.allocation_attribute_usage
        usage.value = str(value)
        usage.save()

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

    def test_allocation_renewal_request_processing_eligibility(self):
        """Test that AllocationRenewalRequests that do not meet all
        conditions for processing are not processed."""
        message_prefix = 'Would process AllocationRenewalRequest {0}'
        approved_status = AllocationRenewalRequestStatusChoice.objects.get(
            name='Approved')

        # A request for a past AllocationPeriod should not be processed.
        fc_existing_request = AllocationRenewalRequest.objects.get(
            post_project__name='fc_existing')
        self.assertEqual(fc_existing_request.status, approved_status)
        fc_existing_request.allocation_period = self.previous_allowance_year
        fc_existing_request.save()

        output, error = self.call_command(
            self.current_allowance_year.id, dry_run=True)
        self.assertNotIn(message_prefix.format(fc_existing_request.id), output)
        self.assertFalse(error)

        # A request for a future AllocationPeriod should not be processed.
        fc_existing_request.allocation_period = self.next_allowance_year
        fc_existing_request.save()

        output, error = self.call_command(
            self.current_allowance_year.id, dry_run=True)
        self.assertNotIn(message_prefix.format(fc_existing_request.id), output)
        self.assertFalse(error)

        # A request with a status other than 'Approved' should not be
        # processed.
        fc_existing_request.allocation_period = self.current_allowance_year
        statuses = AllocationRenewalRequestStatusChoice.objects.all()
        self.assertGreater(statuses.count(), 1)
        fc_message = message_prefix.format(fc_existing_request.id)
        for status in statuses:
            fc_existing_request.status = status
            fc_existing_request.save()
            output, error = self.call_command(
                self.current_allowance_year.id, dry_run=True)
            if status == approved_status:
                self.assertIn(fc_message, output)
            else:
                self.assertNotIn(fc_message, output)
            self.assertFalse(error)

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

    def test_new_project_request_processing_eligibility(self):
        """Test that new project requests that do not meet all
        conditions for processing are not processed."""
        message_prefix = 'Would process SavioProjectAllocationRequest {0}'
        approved_scheduled_status = \
            ProjectAllocationRequestStatusChoice.objects.get(
                name='Approved - Scheduled')

        # A request for a past AllocationPeriod should not be processed.
        fc_existing = Project.objects.get(name='fc_existing')
        fc_existing_request = SavioProjectAllocationRequest.objects.get(
            project=fc_existing)
        fc_existing_request.status = approved_scheduled_status
        fc_existing_request.save()

        # A request for a future AllocationPeriod should not be processed.
        num_service_units = Decimal('300000.00')
        fc_future = self.create_project(
            'fc_future', self.fca, self.next_allowance_year, num_service_units,
            approve=True)
        fc_future_request = SavioProjectAllocationRequest.objects.get(
            project=fc_future)
        self.assertEqual(fc_future_request.status, approved_scheduled_status)

        output, error = self.call_command(
            self.current_allowance_year.id, dry_run=True)
        for request in (fc_existing_request, fc_future_request):
            self.assertNotIn(message_prefix.format(request.id), output)
        self.assertFalse(error)

        # A request with a status other than 'Approved - Scheduled' should not
        # be processed.
        fc_new_request = SavioProjectAllocationRequest.objects.get(
            project__name='fc_new')
        pc_new_request = SavioProjectAllocationRequest.objects.get(
            project__name='pc_new')
        statuses = ProjectAllocationRequestStatusChoice.objects.all()
        self.assertGreater(statuses.count(), 1)
        fc_message = message_prefix.format(fc_new_request.id)
        pc_message = message_prefix.format(pc_new_request.id)
        for status in statuses:
            pc_new_request.status = status
            pc_new_request.save()
            output, error = self.call_command(
                self.current_allowance_year.id, dry_run=True)
            self.assertIn(fc_message, output)
            if status == approved_scheduled_status:
                self.assertIn(pc_message, output)
            else:
                self.assertNotIn(pc_message, output)
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

    def test_project_deactivation_eligibility(self):
        """Test that Projects that do not meet all conditions for
        deactivation are not deactivated."""

        def assert_message_in_command_output(included,
                                             project_name='fc_existing'):
            message_template = (
                'Would deactivate Project {0} ({1}) and reset Service Units.')
            message = message_template.format(fc_existing.id, project_name)
            output, error = self.call_command(
                allocation_period.id, dry_run=True)
            if included:
                self.assertIn(message, output)
            else:
                self.assertNotIn(message, output)
            self.assertFalse(error)

        allocation_period = self.current_allowance_year
        active_status = ProjectStatusChoice.objects.get(name='Active')
        resource = Resource.objects.get(name='Savio Compute')

        fc_existing = Project.objects.get(name='fc_existing')
        accounting_allocation_objects = get_accounting_allocation_objects(
            fc_existing)
        allocation = accounting_allocation_objects.allocation
        # The Project's Allocation's end date must be null or less than the
        # AllocationPeriod's end date.
        self.assertTrue(
            allocation.end_date is None or
            allocation.end_date < allocation_period.start_date)
        # The Project's name must begin with a prefix matching those associated
        # with the AllocationPeriod.
        self.assertTrue(fc_existing.name.startswith('fc_'))
        # The Project's status must be 'Active'.
        self.assertEqual(fc_existing.status, active_status)
        # The Project's Allocation must be for the 'Savio Compute' Resource.
        self.assertIn(resource, allocation.resources.all())

        # A Project meeting all conditions should be deactivated.
        assert_message_in_command_output(True)

        # A Project with a null Allocation end date should be deactivated.
        allocation.end_date = None
        allocation.save()
        assert_message_in_command_output(True)

        # A Project failing to meet all conditions should not be deactivated.

        # Allocation end date is >= AllocationPeriod's start date.
        tmp_allocation_end_date = allocation.end_date
        for offset_days in (0, 1):
            allocation.end_date = (allocation_period.start_date +
                                   timedelta(days=offset_days))
            allocation.save()
            assert_message_in_command_output(False)
        allocation.end_date = tmp_allocation_end_date
        allocation.save()

        assert_message_in_command_output(True)

        # Project name with non-associated or invalid prefix
        tmp_project_name = fc_existing.name
        associated_prefixes = ('fc_', 'pc_')
        invalid_prefixes = ('ac_', 'co_')
        Project.objects.filter(
            name__in=['ic_existing', 'pc_existing']).delete()
        for prefix in ('ac_', 'co_', 'fc_', 'ic_', 'pc_'):
            fc_existing.name = f'{prefix}{fc_existing.name[3:]}'
            fc_existing.save()
            if prefix not in invalid_prefixes:
                assert_message_in_command_output(
                    prefix in associated_prefixes,
                    project_name=fc_existing.name)
            else:
                _, err = self.call_command(allocation_period.id, dry_run=True)
                self.assertTrue(err)
        fc_existing.name = tmp_project_name
        fc_existing.save()

        assert_message_in_command_output(True)

        # Project with non-'Active' status
        other_statuses = ProjectStatusChoice.objects.exclude(
            pk=active_status.pk)
        self.assertTrue(other_statuses.exists())
        for status in other_statuses:
            fc_existing.status = status
            fc_existing.save()
            assert_message_in_command_output(False)
        fc_existing.status = active_status
        fc_existing.save()

        assert_message_in_command_output(True)

        # Allocation not to 'Savio Compute' Resource
        allocation.resources.remove(resource)
        assert_message_in_command_output(False)
        allocation.resources.add(resource)

        assert_message_in_command_output(True)

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

    def test_starts_allowance_year_period(self):
        """Test that an AllocationPeriod representing an allowance year
        is started properly."""
        allocation_period = self.current_allowance_year

        fc_existing = Project.objects.get(name='fc_existing')
        self.assert_existing_project_pre_state(
            self.previous_allowance_year, fc_existing)
        ic_existing = Project.objects.get(name='ic_existing')
        self.assert_existing_project_pre_state(
            self.previous_instructional_period, ic_existing)
        pc_existing = Project.objects.get(name='pc_existing')
        self.assert_existing_project_pre_state(
            self.previous_allowance_year, pc_existing)
        fc_new = Project.objects.get(name='fc_new')
        self.assert_new_project_pre_state(fc_new)
        ic_new = Project.objects.get(name='ic_new')
        self.assert_new_project_pre_state(ic_new)
        pc_new = Project.objects.get(name='pc_new')
        self.assert_new_project_pre_state(pc_new)

        allocation_renewal_request = AllocationRenewalRequest.objects.get(
            post_project=fc_existing)
        self.assertEqual(allocation_renewal_request.status.name, 'Approved')

        pre_time = utc_now_offset_aware()
        self.call_command(allocation_period.id, dry_run=False)
        post_time = utc_now_offset_aware()

        allocation_renewal_request.refresh_from_db()
        self.assertEqual(allocation_renewal_request.status.name, 'Complete')

        fc_existing.refresh_from_db()
        self.assert_post_state_deactivated_renewed(
            fc_existing, pre_time, post_time)
        pc_existing.refresh_from_db()
        self.assert_post_state_deactivated(pc_existing, pre_time, post_time)
        fc_new.refresh_from_db()
        self.assert_post_state_activated(fc_new, pre_time, post_time)
        pc_new.refresh_from_db()
        self.assert_post_state_activated(pc_new, pre_time, post_time)

        # Sanity check for ICA projects: assert no status change.
        ic_existing.refresh_from_db()
        self.assertEqual(ic_existing.status.name, 'Active')
        ic_new.refresh_from_db()
        self.assertEqual(ic_new.status.name, 'New')

    def test_starts_instructional_period(self):
        """Test that an AllocationPeriod representing an instructional
        period is started properly."""
        allocation_period = self.current_instructional_period

        fc_existing = Project.objects.get(name='fc_existing')
        self.assert_existing_project_pre_state(
            self.previous_allowance_year, fc_existing)
        ic_existing = Project.objects.get(name='ic_existing')
        self.assert_existing_project_pre_state(
            self.previous_instructional_period, ic_existing)
        pc_existing = Project.objects.get(name='pc_existing')
        self.assert_existing_project_pre_state(
            self.previous_allowance_year, pc_existing)
        fc_new = Project.objects.get(name='fc_new')
        self.assert_new_project_pre_state(fc_new)
        ic_new = Project.objects.get(name='ic_new')
        self.assert_new_project_pre_state(ic_new)
        pc_new = Project.objects.get(name='pc_new')
        self.assert_new_project_pre_state(pc_new)

        pre_time = utc_now_offset_aware()
        self.call_command(allocation_period.id, dry_run=False)
        post_time = utc_now_offset_aware()

        ic_existing.refresh_from_db()
        self.assert_post_state_deactivated(ic_existing, pre_time, post_time)
        ic_new.refresh_from_db()
        self.assert_post_state_activated(ic_new, pre_time, post_time)

        # Sanity check for FCA/PCA projects: assert no status change.
        fc_existing.refresh_from_db()
        self.assertEqual(fc_existing.status.name, 'Active')
        pc_existing.refresh_from_db()
        self.assertEqual(pc_existing.status.name, 'Active')
        fc_new.refresh_from_db()
        self.assertEqual(fc_new.status.name, 'New')
        pc_new.refresh_from_db()
        self.assertEqual(pc_new.status.name, 'New')
