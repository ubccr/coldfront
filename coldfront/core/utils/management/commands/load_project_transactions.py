from coldfront.core.project.models import Project
from coldfront.core.statistics.models import ProjectTransaction
from dateutil import parser as date_parser
from decimal import Decimal
from django.core.management.base import BaseCommand
import json
import os

"""An admin command that loads ProjectTransactions from a file."""


class Command(BaseCommand):

    help = (
        'Load ProjectTransactions from a jsonl file dumped from the legacy '
        'accounting service.')

    def add_arguments(self, parser):
        parser.add_argument(
            'jsonl',
            help=(
                'The path to the jsonl file containing details of '
                'ProjectTransactions, separated by a newline.'),
            type=self.existent_file)

    def handle(self, *args, **options):
        with open(options['jsonl'], 'r') as jsonl:
            for line in jsonl:
                line = line.strip()
                if not line:
                    continue
                try:
                    self.create_transaction(line)
                except Exception as e:
                    message = (
                        f'Failed to create ProjectTransaction for line: '
                        f'{line}')
                    self.stderr.write(message)

    @staticmethod
    def create_transaction(line):
        data = json.loads(line)
        project = Project.objects.get(name=data['project'])
        date_time = date_parser.parse(data['date_time'])
        allocation = Decimal(data['allocation'])
        ProjectTransaction.objects.create(
            project=project,
            date_time=date_time,
            allocation=allocation)

    @staticmethod
    def existent_file(path):
        path = path.strip()
        if not os.path.exists(path):
            raise FileNotFoundError(f'Invalid path {path}.')
        if not os.path.isfile(path):
            raise IsADirectoryError(f'Invalid file {path}.')
        return path
