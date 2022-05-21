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
from coldfront.core.utils.common import add_argparse_dry_run_argument
from coldfront.core.utils.common import display_time_zone_current_date

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from flags.state import flag_enabled

import logging


"""An admin command that performs allocation-related handling at the
start of the given AllocationPeriod."""


class Command(BaseCommand):

    help = (
        'Initiate the given AllocationPeriod, which entails processing'
        'scheduled new project requests and allocation renewal requests and '
        '(de)activating project allocations.')

    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        parser.add_argument(
            'allocation_period_id',
            help='The ID of the AllocationPeriod.',
            type=int)
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

        dry_run = options['dry_run']

        if not dry_run:
            if not self.is_allocation_period_current(allocation_period):
                raise CommandError(
                    f'AllocationPeriod {allocation_period_id}\'s time range '
                    f'({allocation_period.start_date}, '
                    f'{allocation_period.end_date}) is not current.')

        if flag_enabled('BRC_ONLY'):
            if allocation_period.name.startswith('Allowance Year'):
                self.handle_allowance_year_period(allocation_period, dry_run)
            else:
                self.handle_instructional_period(allocation_period, dry_run)

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
        return num_successes

    def handle_allowance_year_period(self, allocation_period, dry_run):
        """Deactivate all FCA and PCA projects, whose prior
        AllocationPeriod ended just before this one started. Then,
        process all requests for new projects and allocation renewals
        that are scheduled for this period.

        If any deactivations fail, do not proceed with processing
        requests.

        Optionally display updates instead of performing them."""
        fc_projects = Project.objects.filter(
            name__startswith='fc_', status__name='Active')
        fc_num_projects = fc_projects.count()
        fc_num_successes = self.deactivate_projects(fc_projects, dry_run)
        fc_num_failures = fc_num_projects - fc_num_successes

        pc_projects = Project.objects.filter(
            name__startswith='pc_', status__name='Active')
        pc_num_projects = pc_projects.count()
        pc_num_successes = self.deactivate_projects(pc_projects, dry_run)
        pc_num_failures = pc_num_projects - pc_num_successes

        failure_messages = []
        if fc_num_failures > 0:
            failure_messages.append(
                f'{fc_num_failures}/{fc_num_projects} FCA Projects')
        if pc_num_failures > 0:
            failure_messages.append(
                f'{pc_num_failures}/{pc_num_projects} PCA Projects')
        if failure_messages:
            raise CommandError(
                f'Failed to deactivate {" and ".join(failure_messages)}.')

        self.process_new_project_requests(allocation_period, dry_run)
        self.process_allocation_renewal_requests(allocation_period, dry_run)

    def handle_instructional_period(self, allocation_period, dry_run):
        """Deactivate all ICA projects whose Allocations ended before
        this one started. Then, process all requests for new projects
        and allocation renewals that are scheduled for this period.

        Optionally display updates instead of performing them.

        Instructional projects only exist for BRC."""
        expired_instructional_project_pks = set(
            Allocation.objects.filter(
                end_date__isnull=False,
                end_date__lt=allocation_period.start_date,
                project__name__startswith='ic_',
                resources__name='Savio Compute'
            ).values_list('project__pk', flat=True))
        ic_projects = Project.objects.filter(
            pk__in=expired_instructional_project_pks)
        ic_num_projects = ic_projects.count()
        ic_num_successes = self.deactivate_projects(ic_projects, dry_run)
        ic_num_failures = ic_num_projects - ic_num_successes

        if ic_num_failures > 0:
            raise CommandError(
                f'Failed to deactivate {ic_num_failures}/{ic_num_projects} '
                f'ICA Projects.')

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
        given AllocationPeriod. Optionally display updates instead of
        performing them."""
        model = AllocationRenewalRequest
        runner_class = AllocationRenewalProcessingRunner
        eligible_requests = model.objects.filter(
            allocation_period=allocation_period,
            status__name='Approved')
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

        for request in requests:
            try:
                allocation_type = request.allocation_type
                if allocation_type == SavioProjectAllocationRequest.FCA:
                    num_service_units = prorated_allocation_amount(
                        settings.FCA_DEFAULT_ALLOCATION, request.request_time,
                        request.allocation_period)
                elif allocation_type == SavioProjectAllocationRequest.ICA:
                    num_service_units = settings.ICA_DEFAULT_ALLOCATION
                elif allocation_type == SavioProjectAllocationRequest.PCA:
                    num_service_units = prorated_allocation_amount(
                        settings.PCA_DEFAULT_ALLOCATION, request.request_time,
                        request.allocation_period)
                else:
                    message = (
                        f'{model_name} {request.pk} has unexpected allocation '
                        f'type {allocation_type}.')
                    self.stderr.write(self.style.ERROR(message))
                    self.logger.error(message)
                    continue
            except Exception as e:
                num_failures = num_failures + 1
                message = (
                    f'Failed to compute service units to grant to '
                    f'{model_name} {request.pk}. Details:')
                self.stderr.write(self.style.ERROR(message))
                self.stderr.write(self.style.ERROR(e))
                continue

            try:
                runner = runner_class(request, num_service_units)
            except Exception as e:
                num_failures = num_failures + 1
                message = (
                    f'Failed to initialize processing runner for {model_name} '
                    f'{request.pk}. Details:')
                self.stderr.write(self.style.ERROR(message))
                self.stderr.write(self.style.ERROR(e))
                continue

            message_template = (
                f'{{0}} {model_name} with {num_service_units} service units.')
            if dry_run:
                message = message_template.format('Would process')
                self.stdout.write(self.style.WARNING(message))
            else:
                try:
                    runner.run()
                except Exception as e:
                    num_failures = num_failures + 1
                    message = (
                        f'Failed to process {model_name} {request.pk}. '
                        f'Details:')
                    self.stderr.write(self.style.ERROR(message))
                    self.stderr.write(self.style.ERROR(e))
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
