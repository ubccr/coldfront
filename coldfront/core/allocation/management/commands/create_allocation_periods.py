from coldfront.core.allocation.models import AllocationPeriod
from datetime import date
from django.core.management.base import BaseCommand
import logging

"""An admin command that creates pre-defined AllocationPeriods."""


class Command(BaseCommand):

    help = 'Manually create pre-defined AllocationPeriods.'
    logger = logging.getLogger(__name__)

    def handle(self, *args, **options):
        """Create AllocationPeriods with the data defined below. If the
        start_date or end_date of a period with an existing name differs
        from the existing one, update it."""
        periods = [
            {
                'name': 'AY21-22',
                'start_date': date(2021, 6, 1),
                'end_date': date(2022, 5, 31),
            },
        ]
        for period in periods:
            name = period['name']
            start_date = period['start_date']
            end_date = period['end_date']
            try:
                allocation_period = AllocationPeriod.objects.get(name=name)
            except AllocationPeriod.DoesNotExist:
                allocation_period = AllocationPeriod.objects.create(**period)
                message = (
                    f'Created AllocationPeriod {allocation_period.pk} with '
                    f'name {name}, start_date {start_date}, and end_date '
                    f'{end_date}.')
                self.logger.info(message)
                self.stdout.write(self.style.SUCCESS(message))
            except AllocationPeriod.MultipleObjectsReturned:
                message = (
                    f'Unexpectedly found multiple AllocationPeriods named '
                    f'{name}. Skipping.')
                self.stderr.write(self.style.ERROR(message))
            else:
                prev_start_date = allocation_period.start_date
                prev_end_date = allocation_period.end_date
                allocation_period.start_date = start_date
                allocation_period.end_date = end_date
                allocation_period.save()
                message = (
                    f'Updated AllocationPeriod {allocation_period.pk} with '
                    f'name {name} from ({prev_start_date}, {prev_end_date}) '
                    f'to ({start_date}, {end_date}).'
                )
                self.logger.info(message)
                self.stdout.write(self.style.SUCCESS(message))
