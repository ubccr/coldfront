import logging

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.management import BaseCommand, CommandError

from coldfront.api.statistics.utils import get_accounting_allocation_objects
from coldfront.core.allocation.utils_.accounting_utils import set_service_units
from coldfront.core.project.models import Project
from coldfront.core.resource.utils import get_primary_compute_resource_name
from coldfront.core.utils.common import add_argparse_dry_run_argument


class Command(BaseCommand):

    help = 'Command to add SUs to a given project.'
    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        parser.add_argument(
            '--project_name',
            help='Name of project to add SUs to.',
            required=True,
            type=str)
        parser.add_argument(
            '--amount',
            help='Number of SUs to add to a given project.',
            required=True,
            type=int)
        parser.add_argument(
            '--reason',
            help='User given reason for adding SUs.',
            required=True,
            type=str)
        add_argparse_dry_run_argument(parser)

    @staticmethod
    def validate_inputs(options):
        """Returns a tuple of the project object, allocation objects,
        current SU amount, and new SU amount. If inputs are invalid,
        raise a CommandError."""
        # Check that the Project exists.
        project_name = options.get('project_name')
        try:
            project = Project.objects.get(name=project_name)
        except Project.DoesNotExist:
            error_message = f'Requested project {project_name} does not exist.'
            raise CommandError(error_message)

        # Check that the Project has an active Allocation to the primary
        # compute resource.
        resource_name = get_primary_compute_resource_name()
        try:
            accounting_allocation_objects = get_accounting_allocation_objects(
                project)
        except ObjectDoesNotExist:
            error_message = (
                f'Service units may not be added to a Project without an '
                f'active Allocation to "{resource_name}".')
            raise CommandError(error_message)

        # Check that the addition, and the updated number after the addition,
        # are within the acceptable bounds for Service Units.
        addition = Decimal(options.get('amount'))
        current_allowance = Decimal(
            accounting_allocation_objects.allocation_attribute.value)
        updated_allowance = current_allowance + addition

        minimum, maximum = settings.ALLOCATION_MIN, settings.ALLOCATION_MAX
        if addition > maximum:
            error_message = (
                f'The amount of service units to add cannot exceed '
                f'{settings.ALLOCATION_MAX}.')
            raise CommandError(error_message)

        if not (minimum <= updated_allowance <= maximum):
            error_message = (
                f'The updated number of service units ({updated_allowance}) '
                f'must be in the range [{minimum}, {maximum}].')
            raise CommandError(error_message)

        # Check that the reason provided for the update is long enough.
        if len(options.get('reason')) < 20:
            error_message = (
                'The update reason must have at least 20 characters.')
            raise CommandError(error_message)

        return (
            project, accounting_allocation_objects, current_allowance,
            updated_allowance)

    def handle(self, *args, **options):
        """ Add SUs to a given project """
        validated_inputs = self.validate_inputs(options)
        project = validated_inputs[0]
        accounting_allocation_objects = validated_inputs[1]
        current_allowance = validated_inputs[2]
        updated_allowance = validated_inputs[3]

        addition = Decimal(options.get('amount'))
        change_reason = options.get('reason')
        dry_run = options.get('dry_run', False)

        message_text = (
            f'{{0}} {addition} SUs for Project {project.name} and its users, '
            f'{"increasing" if addition > 0 else "decreasing"} its SUs from '
            f'{current_allowance} to {updated_allowance}, with reason '
            f'"{change_reason}".')
        if dry_run:
            message = message_text.format('Would add')
            self.stdout.write(self.style.WARNING(message))
        else:
            set_service_units(
                accounting_allocation_objects,
                allocation_allowance=updated_allowance,
                allocation_change_reason=change_reason,
                user_allowance=updated_allowance,
                user_change_reason=change_reason)
            message = message_text.format('Added')
            self.stdout.write(self.style.SUCCESS(message))
            self.logger.info(message)
