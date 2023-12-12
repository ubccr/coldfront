import os

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from csv import reader

base_dir = settings.BASE_DIR


class Command(BaseCommand):

    def handle(self, *args, **options):
        print('Adding users now ...')
        local_path = os.path.join(base_dir, 'local_data/labs')
        files = os.listdir(local_path)

        lab_list = []
        for f in files:
            f_name = f.split('.')
            if f_name[len(f_name)-1] == 'csv':
                my_file = f_name[len(f_name)-2]+('.csv')
                lab_list.append(my_file)

        for lab in lab_list:
            file_name = lab
            lab_list = list(lab.split('.'))
            lab_name = lab_list[0]
            file_path = os.path.join(base_dir, 'local_data/labs', file_name)
            with open(file_path, 'r') as read_obj:
                csv_reader = reader(read_obj) # opt out the first line
                first_line = read_obj.readline()
                for row in csv_reader:
                    username = row[0]
                    full_name = row[1].split()
                    user, created = get_user_model().objects.get_or_create(
                        username=username,
                        defaults={
                            'username': username,
                            'first_name': full_name[0],
                            'last_name':full_name[-1],
                            'email': row[2],
                            'is_active': True,
                            'is_staff': False,
                            'is_superuser': False,

                        }
                    )
                    # if the user exists, I only need to append this existing user's group
                    if not user.groups.filter(name=lab_name).exists():
                        my_group = Group.objects.get(name=lab_name)
                        my_group.user_set.add(user)
                        print ("user do not exist in", lab_name)

                    if created:
                        groups = lab_name

                        # creates my user object to load data from csv to GUI
                        # create user object
                        group_objs = []
                        for group in groups.split(','):
                            group_obj, _ = Group.objects.get_or_create(name=group.strip()) # gets u the group object based on the group name
                            group_objs.append(group_obj)

                        # add user to group
                        if group_objs:
                            user.groups.add(*group_objs) # add the group object to the user
                        user.save()
            print('Finished adding users for lab:', lab)
