import os

from django.core.management.base import BaseCommand

from coldfront.core.school.models import School

app_commands_dir = os.path.dirname(__file__)


class Command(BaseCommand):
    help = 'Import school data'
    def add_arguments(self, parser):
        default_path = os.path.join(app_commands_dir, 'data', 'school_data.csv')
        parser.add_argument(
            '--csv-file-path',
            type=str,
            default=default_path,
            help='Filesystem path to the tab‑delimited school_data.csv'
        )

    def handle(self, *args, **options):
        print('Adding schools ...')
        file_path = options['csv_file_path']
        School.objects.all().delete()
        with open(file_path, 'r') as fp:
            for line in fp:
                pk, description = line.strip().split('\t')

                school = School(
                    pk=pk,
                    description=description,
                )
                school.save()

        print('Finished adding schools')
