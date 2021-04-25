from coldfront.core.project.models import Project
from coldfront.core.utils.management.commands.utils import get_gspread_worksheet
from coldfront.core.utils.management.commands.utils import get_gspread_worksheet_data
from collections import defaultdict
from django.conf import settings
from django.core.management.base import BaseCommand
import logging

"""An admin command that loads project descriptions for BRC."""


# Settings for the 'All-Project-Descriptions' tab of the 'BRC-Projects'
# spreadsheet.
PROJECT_SPREADSHEET_COLS = {
    'ALLOCATION_TYPES': 3,
    'NAME': 9,
    'DESCRIPTION': 10,
}
PROJECT_SPREADSHEET_ID = '1N6VT5VHN07z4nXhea5AXQXRF8WUDoHbJwWL4PV3C66M'
PROJECT_SPREADSHEET_ROW_START = 2
PROJECT_SPREADSHEET_TAB = 'All-Project-Descriptions'


class Command(BaseCommand):

    help = 'Load descriptions into Projects from BRC spreadsheets.'
    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        # Set Project descriptions.
        description_data = self.get_description_data()
        valid_descriptions = self.get_valid_descriptions(description_data)
        self.set_project_descriptions(valid_descriptions)

    @staticmethod
    def get_description_data():
        """Return a list of lists where each entry corresponds to a
        single project from the project spreadsheet.

        Parameters:
            - None

        Returns:
            - List of lists

        Raises:
            - Exception, if any errors occur
        """
        worksheet = get_gspread_worksheet(
            settings.GOOGLE_OAUTH2_KEY_FILE, PROJECT_SPREADSHEET_ID,
            PROJECT_SPREADSHEET_TAB)
        row_start = PROJECT_SPREADSHEET_ROW_START
        row_end = len(
            worksheet.col_values(PROJECT_SPREADSHEET_COLS['DESCRIPTION']))
        col_start = 1
        col_end = PROJECT_SPREADSHEET_COLS['DESCRIPTION']
        return get_gspread_worksheet_data(
            worksheet, row_start, row_end, col_start, col_end)

    @staticmethod
    def get_valid_descriptions(description_data):
        """Return a mapping from found Project names to the description
        entries found for them.

        Parameters:
            - description_data (list): a list of lists

        Returns:
            - Dictionary

        Raises:
            - None
        """
        allocation_types_column = \
            PROJECT_SPREADSHEET_COLS['ALLOCATION_TYPES'] - 1
        name_column = PROJECT_SPREADSHEET_COLS['NAME'] - 1
        description_column = PROJECT_SPREADSHEET_COLS['DESCRIPTION'] - 1

        # Store descriptions for found Projects.
        found = defaultdict(list)
        for row in description_data:
            allocation_types = row[allocation_types_column].strip().split(', ')
            name = row[name_column].strip().lower()
            description = row[description_column].strip()
            if len(description) < 10:
                continue
            for allocation_type in allocation_types:
                if allocation_type in allocation_types:
                    if allocation_type == 'Faculty Computing Allowance (FCA)':
                        full_name = f'fc_{name}'
                    elif allocation_type == 'Condo Allocation':
                        full_name = f'co_{name}'
                    else:
                        continue
                    try:
                        Project.objects.get(name=full_name)
                    except Project.DoesNotExist:
                        continue
                    found[full_name].append(description)
        return found

    def set_project_descriptions(self, valid_descriptions):
        """For each Project, set its description to the first one found
        in the giving mapping.

        Parameters:
            - valid_descriptions (dict): a dictionary mapping Project
            name to list of descriptions found for it

        Returns:
            - None

        Raises:
            - Exception, if any errors occur
        """
        # Load only the first description found for each Project.
        num_found = len(valid_descriptions)
        for full_name in valid_descriptions:
            try:
                project = Project.objects.get(name=full_name)
            except Project.DoesNotExist:
                continue
            else:
                project.description = valid_descriptions[full_name][0]
                project.save()
                message = f'Set description for Project {full_name}.'
                self.logger.info(message)
                self.stdout.write(self.style.SUCCESS(message))
        message = f'Number of Project descriptions set: {num_found}'
        self.stdout.write(self.style.SUCCESS(message))
