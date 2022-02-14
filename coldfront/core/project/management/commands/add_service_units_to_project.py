import logging
from decimal import Decimal

from django.core.management import BaseCommand, CommandError

from coldfront.core.project.models import Project
from coldfront.core.statistics.models import ProjectTransaction
from coldfront.core.statistics.models import ProjectUserTransaction
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.api.statistics.utils import get_accounting_allocation_objects
from coldfront.api.statistics.utils import set_project_allocation_value
from coldfront.api.statistics.utils import set_project_user_allocation_value
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

    def handle(self, *args, **options):
        """ Set user password for all users in test database """

        project = Project.objects.get(name=options.get('project_name'))
        addition = Decimal(options.get('amount'))
        reason = options.get('reason')
        dry_run = options.get('dry_run', None)

        if not Allocation.objects.get(project=project).resources.filter(name='Savio Compute').exists():
            raise CommandError('Can only add SUs to projects that '
                               'have an allocation in Savio Compute.')

        date_time = utc_now_offset_aware()
        allocation_objects = get_accounting_allocation_objects(project)
        current_allocation = Decimal(allocation_objects.allocation_attribute.value)

        # Compute the new Service Units value.
        allocation = addition + current_allocation

        if dry_run:
            message = f'Would add {addition} additional SUs to project ' \
                      f'{project.name}. This would increase {project.name} ' \
                      f'SUs from {current_allocation} to {allocation}. ' \
                      f'The reason for updating SUs for {project.name} ' \
                      f'would be: {reason}.'

            self.stdout.write(self.style.WARNING(message))

        else:
            # Set the value for the Project.
            set_project_allocation_value(project, allocation)

            # Create a transaction to record the change.
            ProjectTransaction.objects.create(
                project=project,
                date_time=date_time,
                allocation=allocation)

            # Set the reason for the change in the newly-created historical object.
            allocation_objects.allocation_attribute.refresh_from_db()
            historical_allocation_attribute = \
                allocation_objects.allocation_attribute.history.latest("id")
            historical_allocation_attribute.history_change_reason = reason
            historical_allocation_attribute.save()

            # Do the same for each ProjectUser.
            allocation_attribute_type = AllocationAttributeType.objects.get(
                name="Service Units")
            for project_user in project.projectuser_set.all():
                user = project_user.user
                # Attempt to set the value for the ProjectUser. The method returns whether
                # it succeeded; it may not because not every ProjectUser has a
                # corresponding AllocationUser (e.g., PIs). Only proceed with further steps
                # if an update occurred.
                allocation_updated = set_project_user_allocation_value(
                    user, project, allocation)
                if allocation_updated:
                    # Create a transaction to record the change.
                    ProjectUserTransaction.objects.create(
                        project_user=project_user,
                        date_time=date_time,
                        allocation=allocation)
                    # Set the reason for the change in the newly-created historical object.
                    allocation_user = \
                        allocation_objects.allocation.allocationuser_set.get(user=user)
                    allocation_user_attribute = \
                        allocation_user.allocationuserattribute_set.get(
                            allocation_attribute_type=allocation_attribute_type,
                            allocation=allocation_objects.allocation)
                    historical_allocation_user_attribute = \
                        allocation_user_attribute.history.latest("id")
                    historical_allocation_user_attribute.history_change_reason = reason
                    historical_allocation_user_attribute.save()

            message = f"Successfully added {addition} SUs to {project.name}" \
                      f", updating {project.name}'s SUs from " \
                      f"{current_allocation} to {allocation}."

            self.stdout.write(self.style.SUCCESS(message))
