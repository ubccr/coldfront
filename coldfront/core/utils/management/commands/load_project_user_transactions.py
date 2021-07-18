from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectUser
from coldfront.core.statistics.models import ProjectUserTransaction
from dateutil import parser as date_parser
from decimal import Decimal
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
import json
import os

"""An admin command that loads ProjectUserTransactions from a file."""


class Command(BaseCommand):

    help = (
        'Load ProjectUserTransactions from a jsonl file dumped from the '
        'legacy accounting service.')

    cluster_uid_to_new_user_id = {}
    old_user_id_to_cluster_uid = {}

    def add_arguments(self, parser):
        parser.add_argument(
            'jsonl',
            help=(
                'The path to the jsonl file containing details of '
                'ProjectUserTransactions, separated by a newline.'),
            type=self.existent_file)
        parser.add_argument(
            'user_ids_json',
            help=(
                'The path to the json file containing a mapping from User '
                'primary keys in the legacy accounting service to cluster '
                'UIDs.'),
            type=self.existent_file)

    def handle(self, *args, **options):
        self.set_user_mappings(options['user_ids_json'])
        with open(options['jsonl'], 'r') as jsonl:
            for line in jsonl:
                line = line.strip()
                if not line:
                    continue
                try:
                    self.create_transaction(line)
                except Exception as e:
                    message = (
                        f'Failed to create ProjectUserTransaction for line: '
                        f'{line}')
                    self.stderr.write(message)

    def create_transaction(self, line):
        data = json.loads(line)
        project = Project.objects.get(name=data['project'])
        user = User.objects.get(
            id=self.cluster_uid_to_new_user_id[
                self.old_user_id_to_cluster_uid[data['user']]])
        date_time = date_parser.parse(data['date_time'])
        allocation = Decimal(data['allocation'])
        project_user = ProjectUser.objects.get(project=project, user=user)
        ProjectUserTransaction.objects.create(
            project_user=project_user,
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

    def set_user_mappings(self, json_file_path):
        with open(json_file_path, 'r') as user_ids_json:
            for old_id, cluster_uid in json.load(user_ids_json).items():
                self.old_user_id_to_cluster_uid[int(old_id)] = cluster_uid
        for user in User.objects.select_related('userprofile'):
            cluster_uid = user.userprofile.cluster_uid
            if cluster_uid:
                self.cluster_uid_to_new_user_id[cluster_uid] = user.id