import datetime
import os

from django.conf import settings
from django.contrib.auth.models import Group,
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist
from django.db.utils import OperationalError

from csv import reader

from coldfront.core.field_of_science.models import FieldOfScience
from coldfront.core.project.models import (Project, ProjectStatusChoice,
                                            ProjectUser, ProjectUserRoleChoice,
                                            ProjectUserStatusChoice)
from coldfront.core.allocation.models import (AllocationUser,
                                              AllocationUserStatusChoice)
from coldfront.config.env import ENV, PROJECT_ROOT

base_dir = settings.BASE_DIR


class Command(BaseCommand):

    def handle(self, *args, **options):
        print('Adding users now ...')
        file_path = os.path.join(base_dir, 'local_data/labs')
        print("line27, file path is", file_path)
        # arr = os.listdir()
        arr = os.listdir(file_path)

        print("type of arr is", type(arr))
        print("line 30",arr)
        lab_list = []
        for f in arr:
            f_name = f.split('.')
            if (f_name[len(f_name)-1] == 'csv'):
                my_file = f_name[len(f_name)-2]+('.csv')
                lab_list.append(my_file)

        print("line 41: lab_list", lab_list)
        for lab in lab_list:
            print("line 39 lab is:", lab)
            file_name = lab
            lab_list = list(lab.split('.'))
            lab_name = lab_list[0]
            file_path = os.path.join(base_dir, 'local_data/labs', file_name)
            print("line 43 file path is:", file_path)
            # if (file_name != "rc_admin"):
            # open file in read mode
            with open (file_path, 'r') as read_obj:
                csv_reader = reader(read_obj) # opt out the first line
                first_line = read_obj.readline()
                for row in csv_reader:
                    try:
                        username = row[0]
                        print("line52, my username is", username)
                        user = get_user_model().objects.get(username=username)
                        # print("line 54 user is", user)
                        # print("line47",username, "already exist, don't add to database")
                        # if the user exists, I only need to append this existing user's group
                        if not user.groups.filter(name = lab_name).exists():
                            print("line 45",lab_name)
                            my_group = Group.objects.get(name=lab_name)
                            my_group.user_set.add(user)
                            print ("user do not exist in", lab_name)
                        continue
                    # the type of row is
                    except ObjectDoesNotExist:

                        print("jumped to line 68")
                        username = row[0]
                        full_name = row[1]
                        full_name_list = full_name.split()
                        first_name = full_name_list[0]

                        if (len(full_name_list) > 1):
                            last_name = full_name_list[1]

                        else:
                            last_name = "N/A"
                        print("line76 my username is", username)
                        print("line77 my fullname is", full_name)

                        email = row[2]
                        is_active = True
                        is_staff = False
                        is_superuser = False
                        groups = lab_name

                        # creates my user object to load data from csv to GUI
                        # create user object
                        group_objs = []
                        for group in groups.split(','):
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
                    except OperationalError:
                        print("line110")
                        print("jumped to line 64")
                        username = row[0]
                        full_name = row[1]
                        full_name_list = full_name.split()
                        first_name = full_name_list[0]


                        if (len(full_name_list) > 1):
                            last_name = full_name_list[1]

                        else:
                            last_name = "N/A"
                        print("line124 my username is", username)
                        print("line125 my fullname is", full_name)

                        email = row[2]
                        is_active = True
                        is_staff = False
                        is_superuser = False
                        groups = lab_name

                        # creates my user object to load data from csv to GUI
                        # create user object
                        group_objs = []
                        for group in groups.split(','):
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
                        # # add user to group
                        if group_objs:
                            user_obj.groups.add(*group_objs) # add the group object to the user
                        user_obj.save()
            print('Finished adding users for lab:', lab)
