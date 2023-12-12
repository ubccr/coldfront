import os

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
base_dir = settings.BASE_DIR

class Command(BaseCommand):

    def handle(self, *args, **options):
        print('Adding users now ...')
        file_path = os.path.join(base_dir, 'local_data', 'users.tsv')
        print("file path is:",file_path)

        with open(file_path, 'r') as fp:
            for line in fp:
                if line.startswith('#'):
                    continue
                username, first_name, last_name, email, is_active, is_staff, is_superuser, *groups = line.strip().split('#')

                if groups:
                    print("found", groups)
                    groups = groups[0]

                else:
                    print("did not found groups")
                    groups = ''

                 # duplicated user
                user_obj, created = get_user_model().objects.get_or_create(
                    username=username,
                    defaults={
                        'username': username,
                        'first_name': first_name,
                        'last_name': last_name,
                        'email': email,
                        'is_active': is_active,
                        'is_staff': is_staff,
                        'is_superuser': is_superuser,
                    }
                )
                print(username, first_name, last_name, email, is_active, is_staff, is_superuser, groups)
                if not created:
                    print(username, "already exist")
                    continue

                group_objs = []

                for group in groups.split(','):
                    group_obj, _ = Group.objects.get_or_create(name=group.strip())
                    group_objs.append(group_obj)

                print(group_objs)

                if group_objs:
                    print("group_objs exist")
                    user_obj.groups.add(*group_objs)
                if 'pi' in groups.split(','):
                    user_obj.is_pi = True
                user_obj.save()

                print(user_obj)

        print('Finished adding users.')
