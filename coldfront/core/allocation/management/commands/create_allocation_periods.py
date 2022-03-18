from coldfront.core.allocation.models import AllocationPeriod
from datetime import datetime
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
import json
import logging

"""An admin command that loads AllocationPeriods from a JSON file."""


class Command(BaseCommand):

    help = 'Create AllocationPeriods from a JSON.'
    logger = logging.getLogger(__name__)

    date_format = '%Y-%m-%d'

    def add_arguments(self, parser):
        parser.add_argument(
            'json',
            help=(
                f'The path to the JSON file containing a list of objects, '
                f'where each object has a "name", a "start_date", and an '
                f'"end_date", with dates in the format '
                f'"{self.date_format.replace("%", "%%")}".'),
            type=str)
        parser.add_argument(
            '--dry_run',
            action='store_true',
            help='Display updates without performing them.')

    def handle(self, *args, **options):
        """Create AllocationPeriods from the JSON. If a period with a
        given name already exists, update its start_date and
        end_date."""
        periods = self.clean_input_periods(options['json'])
        dry_run = options['dry_run']
        for period in periods:
            name = period['name']
            start_date = period['start_date']
            end_date = period['end_date']
            try:
                allocation_period = AllocationPeriod.objects.get(name=name)
            except AllocationPeriod.DoesNotExist:
                message_template = (
                    f'{{0}} AllocationPeriod {{1}} with '
                    f'name "{name}", start_date {start_date}, and end_date '
                    f'{end_date}.')
                if dry_run:
                    message = message_template.format('Would create', 'PK')
                    self.stdout.write(self.style.WARNING(message))
                else:
                    allocation_period = AllocationPeriod.objects.create(
                        **period)
                    message = message_template.format(
                        'Created', allocation_period.pk)
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
                message_template = (
                    f'{{0}} AllocationPeriod {allocation_period.pk} with '
                    f'name "{name}" from ({prev_start_date}, {prev_end_date}) '
                    f'to ({start_date}, {end_date}).')
                if dry_run:
                    message = message_template.format('Would update')
                    self.stdout.write(self.style.WARNING(message))
                else:
                    allocation_period.start_date = start_date
                    allocation_period.end_date = end_date
                    allocation_period.save()
                    message = message_template.format('Updated')
                    self.logger.info(message)
                    self.stdout.write(self.style.SUCCESS(message))

    def clean_input_periods(self, json_file_path):
        """Return a list of dictionaries with keys "name", "start_date",
        and "end_date", where the dates are datetime.date objects, read
        from the JSON at the given file path. Raise exceptions if data
        cannot be parsed or is invalid."""
        with open(json_file_path, 'r') as f:
            periods = json.load(f)
        for period in periods:
            name = period.get('name', '').strip()
            if not name:
                raise CommandError(f'Period {period} has no name.')
            for key in ('start_date', 'end_date'):
                if key not in period:
                    raise CommandError(f'Period {period} has no {key}.')
                period[key] = datetime.strptime(
                    period[key], self.date_format).date()
        return periods
