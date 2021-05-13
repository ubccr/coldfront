import datetime
import os

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist

from csv import reader

from coldfront.core.field_of_science.models import FieldOfScience
from coldfront.core.project.models import (Project, ProjectStatusChoice,
                                            ProjectUser, ProjectUserRoleChoice,
                                            ProjectUserStatusChoice)

base_dir = settings.BASE_DIR


class Command(BaseCommand):

    def handle(self, *args, **options):
        print('Adding users now ...')
        lab_name = 'kovac_lab'
        file_name = lab_name + '.csv'
        file_path = os.path.join(base_dir, 'local_data', file_name)
        
        # open file in read mode
        with open (file_path, 'r') as read_obj:
            csv_reader = reader(read_obj) # opt out the first line
            first_line = read_obj.readline()  # opt out the first line
            for row in csv_reader:
                try:
                    username = row[0]
                    usage = 666
                    user = User.objects.get(username=username) #user is an instance of my user object

                    print(username, "already exist, don't add to database")
                    # if the user exists, only need to append this existing user's group
                    if not user.groups.filter(name = lab_name).exists():
                        my_group = Group.objects.get(name=lab_name)
                        my_group.user_set.add(user)
                        print ("not exist in kovac_lab")
                    continue
               
                except ObjectDoesNotExist:
                    print(type(row))
                    print("suppose to be userID:",row[0])
                    username = row[0]
                    full_name = row[1] 
                    full_name_list = full_name.split()
                    first_name = full_name_list[0]
                    if (len(full_name_list) > 1):
                        last_name = full_name_list[1]
                     
                    else:
                        last_name = "N/A"
             
                        
                    email = row[2] 
                    is_active = True
                    is_staff = False
                    is_superuser = False
                    groups = lab_name # for now, I manually typed in the group name; later it needs to be automatically read from title

                    # creates my user object to load data from csv to GUI
                    # create user object
                    group_objs = []
                    for group in groups.split(','):
                        print("line55 group is", group)
                        group_obj, _ = Group.objects.get_or_create(name=group.strip()) # gets u the group object based on the group name
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
                    # add user to group
                    if group_objs:
                        user_obj.groups.add(*group_objs) # add the group object to the user
                    user_obj.save()
        print('Finished adding users.')
