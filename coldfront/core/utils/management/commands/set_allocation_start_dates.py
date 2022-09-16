from coldfront.core.allocation.utils import get_project_compute_allocation
from coldfront.core.project.models import Project
from datetime import datetime
from django.core.management.base import BaseCommand
import logging


class Command(BaseCommand):

    help = (
        'Sets Allocation start dates for the Projects listed in the given '
        'file.')

    logger = logging.getLogger(__name__)
    date_format = '%Y-%m-%d'

    def add_arguments(self, parser):
        parser.add_argument(
            'file',
            help=(
                f'The file containing projects to consider. Each row should '
                'be of the form: project_name,{self.date_format}.'))

    def handle(self, *args, **kwargs):
        if not kwargs['file']:
            print('No file provided.')
            return
        with open(kwargs['file']) as list_file:
            for i, entry in enumerate(list_file):
                parts = entry.split(',')
                if len(parts) != 2:
                    print(f'Invalid row {i}: {entry}. Skipping.')
                    continue
                project_name = parts[0].strip().lower()
                date_time = parts[1].strip()
                if not project_name or not date_time:
                    print(f'Invalid row {i}: {entry}. Skipping.')
                    continue
                try:
                    project = Project.objects.get(name=project_name)
                except Project.DoesNotExist:
                    print(f'Project {project_name} does not exist. Skipping.')
                    continue
                try:
                    parsed_date = datetime.strptime(
                        date_time, self.date_format).date()
                except ValueError:
                    print(f'Date time {date_time} is invalid. Skipping.')
                    continue
                self.set_allocation_start_date(project, parsed_date)

    def set_allocation_start_date(self, project, date):
        """Set the start date of the given Project's compute Allocation
        to the given date."""
        try:
            allocation = get_project_compute_allocation(project)
            allocation.start_date = date
            allocation.save()
            self.logger.info(
                f'Set Allocation {allocation.pk} start_date to {date}.')
        except Exception as e:
            self.logger.exception(e)
            print(e)
