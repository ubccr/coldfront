import os

from django.conf import settings
from django.contrib.auth.models import Group, UserDataUsage
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist
base_dir = settings.BASE_DIR

for user in get_user_model().objects.all():
    user.set_password('test1234')
    print(user.username)
    user.save()

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
                try:
                    user = get_user_model().objects.get(username=username)
                    print(username, "already exist")
                    print(username, first_name, last_name, email, is_active, is_staff, is_superuser, groups)

                    continue

                except ObjectDoesNotExist:
                    print("adding new object")
                    print(username, first_name, last_name, email, is_active, is_staff, is_superuser, groups)


                group_objs = []

                for group in groups.split(','):
                    group_obj, _ = Group.objects.get_or_create(name=group.strip())
                    group_objs.append(group_obj)

                user_obj = get_user_model().objects.create(
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    is_active=is_active,
                    is_staff=is_staff,
                    is_superuser=is_superuser,
                )

                print(group_objs)



                if group_objs:
                    print("group_objs exist")
                    user_obj.groups.add(*group_objs)
                if 'pi' in groups.split(','):
                    user_obj.is_pi = True
                user_obj.save()

                print(user_obj)

        print('Finished adding users.')
