from coldfront.api.statistics.utils import get_accounting_allocation_objects
from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.allocation.utils import prorated_allocation_amount
from coldfront.core.project.models import Project
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.project.utils import deactivate_project_and_allocation
from coldfront.core.project.utils_.new_project_utils import SavioProjectProcessingRunner
from coldfront.core.project.utils_.renewal_utils import AllocationRenewalProcessingRunner
from coldfront.core.resource.utils_.allowance_utils.computing_allowance import ComputingAllowance
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.utils.common import add_argparse_dry_run_argument
from coldfront.core.utils.common import display_time_zone_current_date

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db.models import Q

import logging


"""An admin command that performs allocation-related handling at the
start of the given AllocationPeriod."""


class Command(BaseCommand):

    help = (
        'Initiate the given AllocationPeriod, which entails processing'
        'scheduled new project requests and allocation renewal requests and '
        '(de)activating project allocations.')

    logger = logging.getLogger(__name__)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.computing_allowance_interface = ComputingAllowanceInterface()

    def add_arguments(self, parser):
        parser.add_argument(
            'allocation_period_id',
            help='The ID of the AllocationPeriod.',
            type=int)
        parser.add_argument(
            '--skip_deactivations',
            action='store_true',
            help=(
                'Do not deactivate Projects prior to processing requests. '
                'This is useful in case any outstanding requests need to be '
                'processed by re-running the command.'))
        add_argparse_dry_run_argument(parser)

    def handle(self, *args, **options):
        """Perform allocation-type-specific handling for the given
        AllocationPeriod."""
        allocation_period_id = options['allocation_period_id']
        try:
            allocation_period = AllocationPeriod.objects.get(
                pk=allocation_period_id)
        except AllocationPeriod.DoesNotExist:
            raise CommandError(
                f'AllocationPeriod {allocation_period_id} does not exist.')

        skip_deactivations = options['skip_deactivations']
        dry_run = options['dry_run']

        if not dry_run:
            if not self.is_allocation_period_current(allocation_period):
                raise CommandError(
                    f'AllocationPeriod {allocation_period_id}\'s time range '
                    f'({allocation_period.start_date}, '
                    f'{allocation_period.end_date}) is not current.')

        self.handle_allocation_period(
            allocation_period, skip_deactivations, dry_run)

    def deactivate_projects(self, projects, dry_run):
        """Deactivate the given queryset of Projects. Return the number
        of deactivations that succeeded.

        Optionally display updates instead of performing them."""
        num_successes = 0
        for project in projects:
            if dry_run:
                # Retrieve expected database objects to check that they exist.
                try:
                    get_accounting_allocation_objects(project)
                except Exception as e:
                    message = (
                        f'Failed to retrieve expected accounting objects for '
                        f'Project {project.pk} ({project.name}).')
                    self.stderr.write(self.style.ERROR(message))
                    log_message = message + f' Details:\n{e}'
                    self.logger.exception(log_message)
                else:
                    num_successes = num_successes + 1
                    message = (
                        f'Would deactivate Project {project.pk} '
                        f'({project.name}) and reset Service Units.')
                    self.stdout.write(self.style.WARNING(message))
            else:
                try:
                    deactivate_project_and_allocation(project)
                except Exception as e:
                    message = (
                        f'Failed to deactivate Project {project.pk} '
                        f'({project.name}).')
                    self.stderr.write(self.style.ERROR(message))
                    log_message = message + f' Details:\n{e}'
                    self.logger.exception(log_message)
                else:
                    num_successes = num_successes + 1
                    message = (
                        f'Deactivated Project {project.pk} ({project.name}) '
                        f'and reset Service Units.')
                    self.stdout.write(self.style.SUCCESS(message))
                    self.logger.info(message)
        return num_successes

    def get_allowances_for_allocation_period(self, allocation_period):
        """For the given AllocationPeriod, return a list of computing
        allowances (Resource objects) that correspond to the period."""
        all_allowances = self.computing_allowance_interface.allowances()
        filtered_allowances = []
        if allocation_period.name.startswith('Allowance Year'):
            for allowance in all_allowances:
                wrapper = ComputingAllowance(allowance)
                if wrapper.is_yearly():
                    filtered_allowances.append(allowance)
        else:
            for allowance in all_allowances:
                wrapper = ComputingAllowance(allowance)
                if wrapper.is_instructional():
                    filtered_allowances.append(allowance)
        return filtered_allowances

    def get_deactivation_eligible_projects(self, allocation_period,
                                           computing_allowance):
        """Given an AllocationPeriod and a computing allowance (Resource
        object), return a queryset of Projects with the allowance that
        are eligible for deactivation.

        In particular, "Active" Projects with no end dates or end dates
        before the start date of the AllocationPeriod may be
        deactivated."""
        wrapper = ComputingAllowance(computing_allowance)
        if not wrapper.is_periodic():
            raise ValueError(
                f'Unexpected allowance: "{computing_allowance.name}".')
        project_name_prefix = \
            self.computing_allowance_interface.code_from_name(
                computing_allowance.name)
        expired_project_pks = set(
            Allocation.objects.filter(
                (Q(end_date__isnull=True) |
                 Q(end_date__lt=allocation_period.start_date)) &
                Q(project__name__startswith=project_name_prefix) &
                Q(project__status__name='Active') &
                Q(resources__name='Savio Compute')
            ).values_list('project__pk', flat=True))
        return Project.objects.filter(pk__in=expired_project_pks)

    def handle_allocation_period(self, allocation_period, skip_deactivations,
                                 dry_run):
        """Optionally deactivate eligible projects associated with the
        given period. Then, process all requests for new projects and
        allocation renewals that are scheduled for the period.

        If any deactivations fail, do not proceed with processing
        requests.

        Optionally display updates instead of performing them."""
        if not skip_deactivations:
            allowances = self.get_allowances_for_allocation_period(
                allocation_period)

            failure_messages = []
            for allowance in allowances:
                projects = self.get_deactivation_eligible_projects(
                    allocation_period, allowance)
                num_projects = projects.count()
                num_successes = self.deactivate_projects(projects, dry_run)
                num_failures = num_projects - num_successes
                if num_failures > 0:
                    failure_messages.append(
                        f'Failed to deactivate {num_failures}/{num_projects} '
                        f'"{allowance.name}" Projects.')

            if failure_messages:
                raise CommandError(" ".join(failure_messages))

        # New project requests should be processed prior to renewal requests,
        # since a renewal request may depend on a new project request.
        self.process_new_project_requests(allocation_period, dry_run)
        self.process_allocation_renewal_requests(allocation_period, dry_run)

    @staticmethod
    def is_allocation_period_current(allocation_period):
        """Return whether the current date falls in the time range
        covered by the given AllocationPeriod."""
        return (allocation_period.start_date <=
                display_time_zone_current_date() <=
                allocation_period.end_date)

    def process_allocation_renewal_requests(self, allocation_period, dry_run):
        """Process the "Approved" AllocationRenewalRequests for the
        given AllocationPeriod and allowance. Optionally display updates
        instead of performing them."""
        model = AllocationRenewalRequest
        runner_class = AllocationRenewalProcessingRunner
        eligible_requests = model.objects.filter(
            allocation_period=allocation_period, status__name='Approved')
        self.process_requests(model, runner_class, eligible_requests, dry_run)

    def process_new_project_requests(self, allocation_period, dry_run):
        """Process the "Approved - Scheduled"
        SavioProjectAllocationRequests for the given AllocationPeriod.
        Optionally display updates instead of performing them."""
        model = SavioProjectAllocationRequest
        runner_class = SavioProjectProcessingRunner
        eligible_requests = model.objects.filter(
            allocation_period=allocation_period,
            status__name='Approved - Scheduled')
        self.process_requests(model, runner_class, eligible_requests, dry_run)

    def process_requests(self, model, runner_class, requests, dry_run):
        """Given a request model, a runner class for processing
        instances of that model, and a queryset of instances to process,
        run the runner on each instance. Optionally display updates
        instead of performing them."""
        model_name = model.__name__
        num_successes, num_failures = 0, 0

        interface = self.computing_allowance_interface
        cached_allowance_data = {}
        for request in requests:
            try:
                computing_allowance = request.computing_allowance
                if computing_allowance not in cached_allowance_data:
                    wrapper = ComputingAllowance(computing_allowance)
                    data = {
                        'num_service_units': Decimal(
                            interface.service_units_from_name(
                                wrapper.get_name())),
                        'is_prorated': wrapper.are_service_units_prorated(),
                    }
                    cached_allowance_data[computing_allowance] = data
                data = cached_allowance_data[computing_allowance]
                num_service_units = data['num_service_units']
                if data['is_prorated']:
                    num_service_units = prorated_allocation_amount(
                        num_service_units, request.request_time,
                        request.allocation_period)
            except Exception as e:
                num_failures = num_failures + 1
                message = (
                    f'Failed to compute service units to grant to '
                    f'{model_name} {request.pk}: {e}')
                self.stderr.write(self.style.ERROR(message))
                continue

            try:
                runner = runner_class(request, num_service_units)
            except Exception as e:
                num_failures = num_failures + 1
                message = (
                    f'Failed to initialize processing runner for {model_name} '
                    f'{request.pk}: {e}')
                self.stderr.write(self.style.ERROR(message))
                continue

            message_template = (
                f'{{0}} {model_name} {request.pk} with {num_service_units} '
                f'service units.')
            if dry_run:
                message = message_template.format('Would process')
                self.stdout.write(self.style.WARNING(message))
            else:
                try:
                    runner.run()
                except Exception as e:
                    num_failures = num_failures + 1
                    message = (
                        f'Failed to process {model_name} {request.pk}: {e}')
                    self.stderr.write(self.style.ERROR(message))
                    self.logger.exception(e)
                else:
                    num_successes = num_successes + 1
                    message = message_template.format('Processed')
                    self.stdout.write(self.style.SUCCESS(message))

        if not dry_run:
            self.write_statistics(
                model_name, requests.count(), num_successes, num_failures)

    def write_statistics(self, model_name, num_total, num_successes,
                         num_failures):
        """Write success/failure statistics to stdout (or stderr) and to
        the log. The stream to write to and the log level depend on
        whether failures occurred."""
        message = (
            f'Processed {num_total} {model_name}s, with {num_successes} '
            f'successes and {num_failures} failures.')
        if num_failures == 0:
            self.stdout.write(self.style.SUCCESS(message))
            self.logger.info(message)
        else:
            self.stderr.write(self.style.ERROR(message))
            self.logger.error(message)
