import logging
from decimal import Decimal

from django.core.management import BaseCommand, CommandError

from coldfront.config import settings
from coldfront.core.project.models import Project
from coldfront.core.project.management.commands.utils import set_service_units
from coldfront.api.statistics.utils import get_accounting_allocation_objects
from coldfront.core.allocation.models import AllocationAttributeType, Allocation


class Command(BaseCommand):
    help = 'Command to add SUs to a given project.'
    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        parser.add_argument('--project_name',
                            help='Name of project to add SUs to.',
                            type=str,
                            required=True)
        parser.add_argument('--amount',
                            help='Number of SUs to add to a given project.',
                            type=int,
                            required=True)
        parser.add_argument('--reason',
                            help='User given reason for adding SUs.',
                            type=str,
                            required=True)
        parser.add_argument('--dry_run',
                            help='Display updates without performing them.',
                            action='store_true')

    def validate_inputs(self, options):
        """
        Validate inputs to add_service_units_to_project command

        Returns a tuple of the project object, allocation objects, current
        SU amount, and new SU amount
        """

        # Checking if project exists
        project_query = Project.objects.filter(name=options.get('project_name'))
        if not project_query.exists():
            error_message = f"Requested project {options.get('project_name')}" \
                            f" does not exist."
            raise CommandError(error_message)

        # Allocation must be in Savio Compute
        project = project_query.first()
        try:
            allocation_objects = get_accounting_allocation_objects(project)
        except Allocation.DoesNotExist:
            error_message = 'Can only add SUs to projects that have an ' \
                            'allocation in Savio Compute.'
            raise CommandError(error_message)

        addition = Decimal(options.get('amount'))
        current_allocation = Decimal(allocation_objects.allocation_attribute.value)

        # new service units value
        allocation = addition + current_allocation

        # checking SU values
        if addition > settings.ALLOCATION_MAX:
            error_message = f'Amount of SUs to add cannot be greater ' \
                            f'than {settings.ALLOCATION_MAX}.'
            raise CommandError(error_message)

        if allocation < settings.ALLOCATION_MIN or allocation > settings.ALLOCATION_MAX:
            error_message = f'Total SUs for allocation {project.name} ' \
                            f'cannot be less than {settings.ALLOCATION_MIN} ' \
                            f'or greater than {settings.ALLOCATION_MAX}.'
            raise CommandError(error_message)

        if len(options.get('reason')) < 20:
            error_message = f'Reason must be at least 20 characters.'
            raise CommandError(error_message)

        return project, allocation_objects, current_allocation, allocation

    def set_historical_reason(self, obj, reason):
        """Set the latest historical object reason"""
        obj.refresh_from_db()
        historical_obj = obj.history.latest('id')
        historical_obj.history_change_reason = reason
        historical_obj.save()

    def handle(self, *args, **options):
        """ Add SUs to a given project """
        project, allocation_objects, current_allocation, allocation = \
            self.validate_inputs(options)

        addition = Decimal(options.get('amount'))
        reason = options.get('reason')
        dry_run = options.get('dry_run', None)

        if dry_run:
            verb = 'increase' if addition > 0 else 'decrease'
            message = f'Would add {addition} additional SUs to project ' \
                      f'{project.name}. This would {verb} {project.name} ' \
                      f'SUs from {current_allocation} to {allocation}. ' \
                      f'The reason for updating SUs for {project.name} ' \
                      f'would be: "{reason}".'

            self.stdout.write(self.style.WARNING(message))

        else:
            set_service_units(project,
                              allocation_objects,
                              allocation,
                              reason,
                              False)

            message = f'Successfully added {addition} SUs to {project.name} ' \
                      f'and its users, updating {project.name}\'s SUs from ' \
                      f'{current_allocation} to {allocation}. The reason ' \
                      f'was: "{reason}".'

            self.logger.info(message)
            self.stdout.write(self.style.SUCCESS(message))
