import logging

from django.core.management.base import BaseCommand, CommandError

from coldfront.core.project.models import Project

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Changes the allowed number of managers in all projects'

    def add_arguments(self, parser):
        parser.add_argument("max_managers", type=int)

    def handle(self, *args, **kwargs):
        max_managers = kwargs.get("max_managers")
        if max_managers < 1:
            raise CommandError("Max managers must be > 0")
        
        project_objs = Project.objects.all()
        for project_obj in project_objs:
            project_obj.max_managers = max_managers
            project_obj.save()

        logger.info(f"All projects' max managers were set to {max_managers}")
