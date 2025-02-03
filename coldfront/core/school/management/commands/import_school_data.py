import os

from django.core.management.base import BaseCommand

from coldfront.core.school.models import School

app_commands_dir = os.path.dirname(__file__)


class Command(BaseCommand):
    help = 'Import school data'

    def handle(self, *args, **options):
        print('Adding schools ...')
        file_path = os.path.join(app_commands_dir, 'data', 'school_data.csv')
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
