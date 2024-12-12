"""Change the Project of the Allocation with the given ID to the project with the given title."""
from django.core.management.base import BaseCommand
from coldfront.core.allocation.models import Allocation
from coldfront.core.project.models import Project

class Command(BaseCommand):
    help = 'Change the Project of the Allocation with the given ID to the project with the given title.'

    def add_arguments(self, parser):
        parser.add_argument('allocation_id', type=int)
        parser.add_argument('project_title', type=str)

    def handle(self, *args, **options):
        allocation_id = options['allocation_id']
        project_title = options['project_title']
        allocation = Allocation.objects.get(pk=allocation_id)
        project = Project.objects.get(title=project_title)
        allocation.project = project
        allocation.save()
        self.stdout.write(self.style.SUCCESS(f'Allocation {allocation_id} is now in project {project_title}'))
        return

