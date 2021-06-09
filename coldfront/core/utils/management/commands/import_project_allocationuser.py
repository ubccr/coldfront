import datetime
import os

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist

from csv import reader

from coldfront.core.field_of_science.models import FieldOfScience
from coldfront.core.project.models import (Project, ProjectStatusChoice,
                                            ProjectUser, ProjectUserRoleChoice,
                                            ProjectUserStatusChoice)
from coldfront.core.allocation.models import (AllocationUser,
                                              AllocationUserStatusChoice)

base_dir = settings.BASE_DIR


class Command(BaseCommand):

    def handle(self, *args, **options):
        print('Adding users now ...')
        lab_name = input("Please type lab name: ")
        file_name = lab_name + '.csv'
        file_path = os.path.join(base_dir, 'local_data', file_name)

        # open file in read mode
        with open (file_path, 'r') as read_obj:
            csv_reader = reader(read_obj) # opt out the first line
            first_line = read_obj.readline()
            for row in csv_reader:
                try:
                    username = row[0]
                    user_usage = row[6]
                    print("testing user_usage", user_usage)
                    user = get_user_model().objects.get(username=username)
                    print("line37.9", user.username)
                    # a = AllocationUser()
                    allocation_draft = AllocationUser.objects.create(
                        allocation = allocation,
                        user = user,
                        status = status,
                        usage = usage,
                        unit = unit,
                        history = history
                    )

                    allocation_draft.save()


                    print(username, "already exist, don't add to database")
                    # if the user exists, I only need to append this existing user's group
                    if not user.groups.filter(name = lab_name).exists():
                        my_group = Group.objects.get(name=lab_name)
                        my_group.user_set.add(user)
                        print ("user do not exist in", lab_name)
                    continue
                # the type of row is
                except ObjectDoesNotExist:

                    username = row[0]
                    full_name = row[1]
                    full_name_list = full_name.split()
                    first_name = full_name_list[0]
                    user_usage = row[6]
                    print("line58", username, "has usage", user_usage)
                    if (len(full_name_list) > 1):
                        last_name = full_name_list[1]

                    else:
                        last_name = "N/A"


                    email = row[2]
                    is_active = True
                    is_staff = False
                    is_superuser = False
                    groups = lab_name

                    # creates my user object to load data from csv to GUI
                    # create user object
                    group_objs = []
                    for group in groups.split(','):
                        print("line55 group is", group)
                        group_obj, _ = Group.objects.get_or_create(name=group.strip()) # gets u the group object based on the group name
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
                    # add user to group
                    if group_objs:
                        user_obj.groups.add(*group_objs) # add the group object to the user
                    user_obj.save()
        print('Finished adding users.')