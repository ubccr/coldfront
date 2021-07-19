from coldfront.core.project.models import Project
from coldfront.core.statistics.models import ProjectTransaction
from django.core.management.base import BaseCommand

"""An admin command that prints a list of Project names and their
latest transaction dates."""


class Command(BaseCommand):

    help = 'List Projects and their latest transaction dates.'

    def handle(self, *args, **options):
        for project in Project.objects.all():
            try:
                transaction = ProjectTransaction.objects.filter(
                    project=project).latest('date_time')
                date_time = transaction.date_time.strftime('%Y-%m-%dT%H:%M:%S')
            except Exception as e:
                continue
            self.stdout.write(f'{project.name},{date_time}')
