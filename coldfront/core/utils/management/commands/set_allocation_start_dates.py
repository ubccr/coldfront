from coldfront.core.allocation.utils import get_project_compute_allocation
from coldfront.core.project.models import Project
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
import logging


class Command(BaseCommand):

    help = (
        "Sets Allocation start dates for the Projects listed in the given "
        "file.")

    logger = logging.getLogger(__name__)
    time_format = "%Y-%m-%dT%H:%M:%S"
    time_zone = timezone.utc

    def add_arguments(self, parser):
        parser.add_argument(
            "--file", help=(
                f"The file containing projects to consider. Each row should "
                "be of the form: project_name,{self.time_format}."))

    def handle(self, *args, **kwargs):
        if not kwargs["file"]:
            print("No file provided.")
            return
        with open(kwargs["file"]) as list_file:
            for i, entry in enumerate(list_file):
                parts = entry.split(",")
                if len(parts) != 2:
                    print(f"Invalid row {i}: {entry}. Skipping.")
                    continue
                project_name, date_time = parts[0].strip(), parts[1].strip()
                if not project_name or not date_time:
                    print(f"Invalid row {i}: {entry}. Skipping.")
                    continue
                try:
                    project = Project.objects.get(name=project_name)
                except Project.DoesNotExist:
                    print(f"Project {project_name} does not exist. Skipping.")
                    continue
                try:
                    parsed_date_time = datetime.strptime(
                        date_time, self.time_format).replace(
                            tzinfo=self.time_zone)
                except ValueError:
                    print(f"Date time {date_time} is invalid. Skipping.")
                    continue
                self.set_allocation_start_date(project, parsed_date_time)

    def set_allocation_start_date(self, project, date_time):
        """Set the start date of the given Project's compute Allocation
        to the given value."""
        try:
            allocation = get_project_compute_allocation(project)
            allocation.start_date = date_time
            allocation.save()
            self.logger.info(
                f"Set Allocation {allocation.pk} start_date to {date_time}.")
        except Exception as e:
            self.logger.exception(e)
            print(e)
