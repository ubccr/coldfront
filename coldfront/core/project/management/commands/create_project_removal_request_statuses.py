from coldfront.core.project.models import ProjectUserRemovalRequestStatusChoice
from django.core.management.base import BaseCommand
import logging

"""Command to create ProjectUserRemovalRequestStatusChoice"""


class Command(BaseCommand):

    help = 'Create 3 ProjectUserRemovalRequestStatusChoice with names ' \
           'Pending, Processing, Complete.'
    logger = logging.getLogger(__name__)

    def handle(self, *args, **options):
        """Create AllocationPeriods with the data defined below. If the
        start_date or end_date of a period with an existing name differs
        from the existing one, update it."""
        for name in ['Pending', 'Processing', 'Complete']:
            try:
                removal_request_status = ProjectUserRemovalRequestStatusChoice.objects.get(name=name)
                message = (
                    f'ProjectUserRemovalRequestStatusChoice '
                    f'{removal_request_status.pk} with name {name} '
                    f'already exists.')
                self.logger.info(message)
                self.stdout.write(self.style.SUCCESS(message))
            except ProjectUserRemovalRequestStatusChoice.DoesNotExist:
                removal_request_status = ProjectUserRemovalRequestStatusChoice.objects.create(name=name)
                message = (
                    f'Created ProjectUserRemovalRequestStatusChoice '
                    f'{removal_request_status.pk} with name {name}.')
                self.logger.info(message)
                self.stdout.write(self.style.SUCCESS(message))
            except ProjectUserRemovalRequestStatusChoice.MultipleObjectsReturned:
                message = (
                    f'Unexpectedly found multiple '
                    f'ProjectUserRemovalRequestStatusChoice named {name}.'
                    f' Skipping.')
                self.stderr.write(self.style.ERROR(message))