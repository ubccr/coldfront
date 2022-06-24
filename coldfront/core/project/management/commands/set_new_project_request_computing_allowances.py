import logging

from django.core.management.base import BaseCommand

from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.utils.common import add_argparse_dry_run_argument


"""An admin command that sets the computing allowances (Resources) for
SavioProjectAllocationRequests."""


class Command(BaseCommand):

    help = 'Set computing allowances for SavioProjectAllocationRequests.'

    logger = logging.getLogger(__name__)

    def __init__(self, *args, **kwargs):
        """Instantiate an interface for retrieving computing
        allowances."""
        super().__init__(*args, **kwargs)
        self.interface = ComputingAllowanceInterface()

    def add_arguments(self, parser):
        add_argparse_dry_run_argument(parser)

    def handle(self, *args, **options):
        """Set the computing_allowance field for each request based on
        the value of the allocation_type field."""
        dry_run = options['dry_run']
        for request in SavioProjectAllocationRequest.objects.all():
            self.set_computing_allowance_for_request(request, dry_run=dry_run)

    def set_computing_allowance_for_request(self, request, dry_run=False):
        """Set the computing allowance (Resource) for the given
        SavioProjectAllocationRequest. Optionally display the update
        instead of performing it."""
        allocation_type = request.allocation_type
        allowance = self.interface.resource_from_name_short(allocation_type)
        message_template = (
            f'{{0}} computing allowance for SavioProjectAllocationRequest '
            f'{request.id} ({request.project.name}) to Resource '
            f'{allowance.pk} ({allowance.name}), based on allocation_type '
            f'{allocation_type}.')
        if dry_run:
            message = message_template.format('Would update')
            self.stdout.write(self.style.WARNING(message))
        else:
            request.computing_allowance = allowance
            request.save()
            message = message_template.format('Updated')
            self.stdout.write(self.style.SUCCESS(message))
            self.logger.info(message)
