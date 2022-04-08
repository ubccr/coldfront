from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.allocation.utils import prorated_allocation_amount
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.project.utils_.new_project_utils import SavioProjectProcessingRunner
from coldfront.core.project.utils_.renewal_utils import AllocationRenewalProcessingRunner
from coldfront.core.utils.common import add_argparse_dry_run_argument
from coldfront.core.utils.common import display_time_zone_current_date
from django.conf import settings
from django.core.management.base import BaseCommand

import logging


"""An admin command that processes allocation renewal requests and new
project requests that have been approved and scheduled for processing by
the time the command runs."""


class Command(BaseCommand):

    help = (
        'Process allocation renewal requests and new project requests that '
        'have been approved and scheduled for processing by the current time.')

    logger = logging.getLogger(__name__)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.date = display_time_zone_current_date()

    def add_arguments(self, parser):
        """Define subcommands with different functions."""
        subparsers = parser.add_subparsers(
            dest='subcommand',
            help='The subcommand to run.',
            title='subcommands')
        subparsers.required = True
        self.add_subparsers(subparsers)

    @staticmethod
    def add_subparsers(subparsers):
        """Add subcommands and their respective parsers."""
        all_parser = subparsers.add_parser('all', help='Run all subcommands.')
        add_argparse_dry_run_argument(all_parser)

        allocation_renewal_requests_parser = subparsers.add_parser(
            'allocation_renewal_requests',
            help='Process scheduled allocation renewal requests.')
        add_argparse_dry_run_argument(allocation_renewal_requests_parser)

        new_project_requests_parser = subparsers.add_parser(
            'new_project_requests',
            help='Process scheduled new project requests.')
        add_argparse_dry_run_argument(new_project_requests_parser)

    def handle(self, *args, **options):
        """Call the handler for the provided subcommand."""
        subcommand = options['subcommand']
        handler = getattr(self, f'handle_{subcommand}')
        handler(*args, **options)

    def handle_all(self, *args, **options):
        """Handle the 'all' subcommand."""
        ordered_subcommands = [
            'allocation_renewal_requests',
            'new_project_requests',
        ]
        for subcommand in ordered_subcommands:
            handler = getattr(self, f'handle_{subcommand}')
            handler(*args, **options)

    def handle_allocation_renewal_requests(self, *args, **options):
        """Handle the 'allocation_renewal_requests' subcommand."""
        model = AllocationRenewalRequest
        runner_class = AllocationRenewalProcessingRunner
        eligible_requests = model.objects.filter(
            allocation_period__start_date__lte=self.date,
            status__name='Approved')
        dry_run = options['dry_run']
        self.process_requests(model, runner_class, eligible_requests, dry_run)

    def handle_new_project_requests(self, *args, **options):
        """Handle the 'new_project_requests' subcommand."""
        model = SavioProjectAllocationRequest
        runner_class = SavioProjectProcessingRunner
        eligible_requests = model.objects.filter(
            allocation_period__start_date__lte=self.date,
            status__name='Approved - Scheduled')
        dry_run = options['dry_run']
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
                # TODO: Set this dynamically when supporting other types.
                num_service_units = prorated_allocation_amount(
                    settings.FCA_DEFAULT_ALLOCATION, request.request_time,
                    request.allocation_period)
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
