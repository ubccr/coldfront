from coldfront.core.project.models import Project
from coldfront.core.statistics.models import Node
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
import json
import os

"""An admin command that loads Jobs from a file."""


class Command(BaseCommand):

    help = (
        'Load Jobs from a jsonl file dumped from the legacy accounting '
        'service.')

    cluster_uid_to_new_user_id = {}
    node_name_to_id = {}
    old_user_id_to_cluster_uid = {}
    project_name_to_id = {}

    def add_arguments(self, parser):
        parser.add_argument(
            'old_jsonl',
            help=(
                'The path to the jsonl file containing individual jobs to '
                'create, separated by a newline.'),
            type=self.existent_file)
        parser.add_argument(
            'user_ids_json',
            help=(
                'The path to the json file containing a mapping from User '
                'primary keys in the legacy accounting service to cluster '
                'UIDs.'),
            type=self.existent_file)
        parser.add_argument(
            'new_jsonl', help='The path to the jsonl file to generate.')

    def handle(self, *args, **options):
        self.set_node_mapping()
        self.set_project_mapping()
        self.set_user_mappings(options['user_ids_json'])
        with open(options['old_jsonl'], 'r') as old_jsonl:
            with open(options['new_jsonl'], 'w') as new_jsonl:
                for line in old_jsonl:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        new_line = self.transform(line)
                    except Exception as e:
                        message = f'Failed to transform line: {line}'
                        self.stderr.write(message)
                    new_jsonl.write(f'{new_line}\n')

    @staticmethod
    def existent_file(path):
        path = path.strip()
        if not os.path.exists(path):
            raise FileNotFoundError(f'Invalid path {path}.')
        if not os.path.isfile(path):
            raise IsADirectoryError(f'Invalid file {path}.')
        return path

    def set_node_mapping(self):
        for node in Node.objects.all():
            self.node_name_to_id[node.name] = node.id

    def set_project_mapping(self):
        for project in Project.objects.all():
            self.project_name_to_id[project.name] = project.id

    def set_user_mappings(self, json_file_path):
        with open(json_file_path, 'r') as user_ids_json:
            for old_id, cluster_uid in json.load(user_ids_json).items():
                self.old_user_id_to_cluster_uid[int(old_id)] = cluster_uid
        for user in User.objects.select_related('userprofile'):
            cluster_uid = user.userprofile.cluster_uid
            if cluster_uid:
                self.cluster_uid_to_new_user_id[cluster_uid] = user.id

    def transform(self, line):
        data = json.loads(line)
        data['model'] = 'statistics.job'
        fields = data['fields']
        fields['userid'] = self.cluster_uid_to_new_user_id[
            self.old_user_id_to_cluster_uid[fields['userid']]]
        fields['accountid'] = self.project_name_to_id[fields['accountid']]
        fields['modified'] = fields.pop('updated')
        fields['nodes'] = [self.node_name_to_id[n] for n in fields['nodes']]
        return json.dumps(data)
