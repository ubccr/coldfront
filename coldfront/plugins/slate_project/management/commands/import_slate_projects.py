import time

from django.core.management.base import BaseCommand, CommandError
from coldfront.plugins.slate_project.utils import import_slate_projects


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument("--json", type=str)
        parser.add_argument("--out", type=str)
        parser.add_argument("--limit", type=int)

    def handle(self, *args, **kwargs):
        if not kwargs.get("json"):
            raise CommandError("JSON file does not exist")
        
        if not kwargs.get("out"):
            raise CommandError("Out file does not exist")
        
        if not kwargs.get("out"):
            raise CommandError("Please provide your username")
        
        if kwargs.get("limit") is not None and kwargs.get("limit") <= 0:
            raise CommandError("The limit must be > 0")

        print('Importing Slate Projects...')
        start_time = time.time()
        import_slate_projects(kwargs.get("limit"), kwargs.get("json"), kwargs.get("out"), kwargs.get("user"))
        print(f'Time elapsed: {time.time() - start_time}')
