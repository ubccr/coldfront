from coldfront.core.allocation.models import AllocationPeriod
from datetime import datetime
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from flags.state import flag_enabled

import json
import logging
import os

"""An admin command that creates AllocationPeriods."""


class Command(BaseCommand):

    help = 'Create AllocationPeriods from a JSON.'
    logger = logging.getLogger(__name__)

    date_format = '%Y-%m-%d'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry_run',
            action='store_true',
            help='Display updates without performing them.')

    def handle(self, *args, **options):
        """Create AllocationPeriods. If a period with a given name
        already exists, update its start_date and end_date."""
        periods = self.clean_periods(self.get_allocation_periods())
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
                if start_date == prev_start_date and end_date == prev_end_date:
                    # No update needed.
                    continue
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

    def clean_periods(self, periods):
        """Given a list of dictionaries, validate that each has the keys
        "name", "start_date", and "end_date", where the dates are in the
        form self.date_format. Return the list with the dates converted
        into date objects. Raise exceptions if data cannot be parsed or
        are invalid."""
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

    @staticmethod
    def get_allocation_periods():
        """Return a list of dictionaries representing AllocationPeriods,
        based on the current deployment."""
        periods = []

        relative_json_path = None
        if flag_enabled('BRC_ONLY'):
            relative_json_path = 'data/brc_allocation_periods.json'
        if flag_enabled('LRC_ONLY'):
            relative_json_path = 'data/lrc_allocation_periods.json'

        if relative_json_path is not None:
            absolute_json_path = os.path.join(
                os.path.dirname(__file__), relative_json_path)
            with open(absolute_json_path, 'r') as f:
                period_list = json.load(f)
            periods.extend(period_list)

        return periods
