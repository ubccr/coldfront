from coldfront.core.statistics.models import Node
from django.core.management.base import BaseCommand
import logging
import os

"""An admin command that loads Nodes from a file."""


class Command(BaseCommand):

    help = 'Load Nodes from a file.'
    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        parser.add_argument(
            'file',
            help=(
                'The path to the file containing names of nodes to create, '
                'separated by a newline.'),
            type=self.existent_file)

    def handle(self, *args, **options):
        num_created = 0
        with open(options['file'], 'r') as f:
            for line in f:
                name = line.strip()
                if not name:
                    continue
                _, created = Node.objects.get_or_create(name=name)
                num_created = num_created + int(created)
        message = f'Created {num_created} Nodes.'
        self.stdout.write(self.style.SUCCESS(message))
        self.logger.info(message)

    @staticmethod
    def existent_file(path):
        path = path.strip()
        if not os.path.exists(path):
            raise FileNotFoundError(f'Invalid path {path}.')
        if not os.path.isfile(path):
            raise IsADirectoryError(f'Invalid file {path}.')
        return path
