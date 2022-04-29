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
        """TODO"""
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
        """Deactivate the given queryset of Projects. Return whether
        all deactivations succeeded.

        Optionally display updates instead of performing them."""
        # TODO: dry_run: ensure that expected objects exist.
        success = True
        for project in projects:
            try:
                deactivate_project_and_allocation(project)
            except Exception as e:
                # TODO
                success = False
        return success

    def handle_allowance_year_period(self, allocation_period, dry_run):
        """Deactivate all FCA and PCA projects, whose prior
        AllocationPeriod ended just before this one started. Then,
        process all requests for new projects and allocation renewals
        that are scheduled for this period.

        Optionally display updates instead of performing them."""

        fc_projects = Project.objects.filter(name__startswith='fc_')
        fc_deactivations_successful = self.deactivate_projects(
            fc_projects, dry_run)

        pc_projects = Project.objects.filter(name__startswith='pc_')
        pc_deactivations_successful = self.deactivate_projects(
            pc_projects, dry_run)

        # TODO
        if not fc_deactivations_successful:
            raise CommandError()
        if not pc_deactivations_successful:
            raise CommandError()

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
        ic_deactivations_successful = self.deactivate_projects(
            ic_projects, dry_run)

        # TODO
        if not ic_deactivations_successful:
            raise CommandError()

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
