from coldfront.core.billing.models import BillingActivity
from coldfront.core.billing.models import BillingProject
from django.core.management.base import BaseCommand

import logging
import openpyxl
import os

"""An admin command that updates the set of BillingProject and
BillingActivity objects in the database. """


logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = (
        'Creates or updates BillingProject and BillingActivity objects, based '
        'on an Excel spreadsheet containing valid pairs. Invalidate any that '
        'are not in the file.')

    def add_arguments(self, parser):
        parser.add_argument(
            'file',
            help=(
                'The path to the file where each row contains a Project ID, '
                'a Project description, an Activity ID, and an Activity '
                'description.'))

    def handle(self, *args, **options):
        """Iterate over the file, creating and updating BillingProject
        and BillingActivity objects. Always update the descriptions
        using the first instance seen. Invalidate any BillingActivity
        objects not in the file."""
        file_path = options['file']
        if not (os.path.exists(file_path) and os.path.isfile(file_path)):
            raise FileNotFoundError(f'File {file_path} does not exist.')

        wb = openpyxl.load_workbook(file_path)
        sheet = wb.worksheets[0]

        projects_by_id = {}
        activity_id_pairs = set()
        valid_activity_pks = set()

        kwargs = {
            'min_row': 3,
            'min_col': 1,
            'max_col': 5,
            'values_only': True,
        }
        for row in sheet.iter_rows(**kwargs):
            project_id, project_desc, _, activity_id, activity_desc = [
                x.strip() for x in row]

            if project_id not in projects_by_id:
                project, _ = BillingProject.objects.update_or_create(
                    identifier=project_id,
                    defaults={'description': project_desc})
                projects_by_id[project_id] = project

            id_pair = (project_id, activity_id)
            if id_pair not in activity_id_pairs:
                activity, _ = BillingActivity.objects.update_or_create(
                    billing_project=projects_by_id[project_id],
                    identifier=activity_id,
                    defaults={'description': activity_desc, 'is_valid': True})
                activity_id_pairs.add(id_pair)
                valid_activity_pks.add(activity.pk)

        # Invalidate other existing BillingActivities.
        BillingActivity.objects.exclude(
            pk__in=valid_activity_pks).update(is_valid=False)
