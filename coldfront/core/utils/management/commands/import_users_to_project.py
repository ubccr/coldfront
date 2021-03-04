import os

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand, CommandError


base_dir = settings.BASE_DIR

for user in User.objects.all():
    user.set_password('test1234')
    print(user.username)
    user.save()

class Command(BaseCommand):

    def handle(self, *args, **options):
        print('Adding users to projects ...')
        file_path = os.path.join(base_dir, 'local_data', 'users_to_projects.tsv')
        print("line 13:",file_path)
       
        with open(file_path, 'r') as fp:
            for line in fp:
                if line.startswith('#'):
                    continue
                username, *project_names = line.strip().split('\t')
            
                print(username, project_names)
                for user in User.objects.all():
                    if (user.username == username):
                        print("user found!!!")
                        # add user to the project
                        for project in Project.objects:
                            if project.title in project_names:
                                print(project)
               

        print('Finished adding users to projects.')
