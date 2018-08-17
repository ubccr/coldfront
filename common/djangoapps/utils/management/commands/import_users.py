import os

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand, CommandError

base_dir = settings.BASE_DIR


class Command(BaseCommand):

    def handle(self, *args, **options):
        print('Adding users ...')
        file_path = os.path.join(base_dir, 'local_data', 'users.tsv')
        User.objects.all().delete()
        Group.objects.all().delete()
        with open(file_path, 'r') as fp:
            for line in fp:
                if line.startswith('#'):
                    continue
                username, first_name, last_name, email, is_active, is_staff, is_superuser, *groups = line.strip().split('\t')

                if groups:
                    groups = groups[0]
                else:
                    groups = ''
                # print(username, first_name, last_name, email, is_active, is_staff, is_superuser, groups)
                group_objs = []
                for group in groups.split(','):
                    group_obj, _ = Group.objects.get_or_create(name=group.strip())
                    group_objs.append(group_obj)

                user_obj = User.objects.create(
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    is_active=is_active,
                    is_staff=is_staff,
                    is_superuser=is_superuser,
                )
                if group_objs:
                    user_obj.groups.add(*group_objs)
                if 'pi' in groups.split(','):
                    user_obj.is_pi = True
                user_obj.save()

                # print(user_obj)

        print('Finished adding users.')
