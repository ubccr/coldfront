import os
import csv
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist
base_dir = settings.BASE_DIR

for user in User.objects.all():
    user.set_password('test1234')
    print(user.username)
    user.save()

class Command(BaseCommand):

    def handle(self, *args, **options):
        print('Adding users now ...')
        file_path = os.path.join(base_dir, 'local_data', 'giribet_lab.csv')
        print("line 13:",file_path)

        # Question begin : why do we delete existing users when we import users?
        # User.objects.all().delete()
        # Group.objects.all().delete()
        # Question end : why do we delete existing users when we import users?

        with open(file_path, 'r') as fp:
            for line in fp:
                if line.startswith('#'):
                    continue
                username, first_name, last_name, email, is_active, is_staff, is_superuser, *groups = line.strip().split('\t')
                if groups:
                    groups = groups[0]
                else:
                    groups = ''
                try:
                    user = User.objects.get(username=username)
                    print(username, "already exist")
                    continue
                    # do we want to update groups as well? 
                except ObjectDoesNotExist:
                    print(username, first_name, last_name, email, is_active, is_staff, is_superuser, groups)
                    
                
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

                print(user_obj)

        print('Finished adding users.')
