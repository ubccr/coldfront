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

for user in User.objects.all():
    user.set_password('test1234')
    #print(user.username)
    user.save()

class Command(BaseCommand):

    def handle(self, *args, **options):
        print('Adding users now ...')
        # read 'xxxxx_lab.csv' file
        lab_name = input("Please type lab name: ")
        file_name = lab_name + '.csv'
        file_path = os.path.join(base_dir, 'local_data', file_name)
        # print("line 13:",file_path)
        # open file in read mode
        with open (file_path, 'r') as read_obj:
            csv_reader = reader(read_obj) # opt out the first line
            first_line = read_obj.readline()  
            for row in csv_reader:
                try:
                    username = row[0]
                    user = User.objects.get(username=username)
                    print(username, "already exist, don't add to database")
                    # if the user exists, I only need to append this existing user's group
                    if not user.groups.filter(name = lab_name).exists():
                        my_group = Group.objects.get(name=lab_name)
                        my_group.user_set.add(user)
                        print ("user do not exist in", lab_name)
                    continue
                # the type of row is 
                except ObjectDoesNotExist:
                    # print(type(row))
                    # print("suppose to be userID:",row[0])
                    username = row[0]
                    full_name = row[1] 
                    full_name_list = full_name.split()
                    first_name = full_name_list[0]
                    if (len(full_name_list) > 1):
                        last_name = full_name_list[1]
                        # print("2,",last_name)
                    else:
                        last_name = "N/A"
                        # print("1,",last_name)
                        
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

        # now adding projects from users and groups

        # project_status_choices = {}
        # project_status_choices['Active'] = ProjectStatusChoice.objects.get(name='Active')
        # project_status_choices['Archived'] = ProjectStatusChoice.objects.get(name='Archived')
        # project_status_choices['New'] = ProjectStatusChoice.objects.get(name='New')

        # project_user_role_choices = {}
        # project_user_role_choices['PI'] = ProjectUserRoleChoice.objects.get(name='Manager')
        # project_user_role_choices['U'] = ProjectUserRoleChoice.objects.get(name='User')
        # project_user_role_choices['M'] = ProjectUserRoleChoice.objects.get(name='Manager')
        # project_user_role_choices['Manager'] = ProjectUserRoleChoice.objects.get(name='Manager')

        # project_user_status_choices = {}
        # project_user_status_choices['ACT'] = ProjectUserStatusChoice.objects.get(name='Active')
        # project_user_status_choices['PEA'] = ProjectUserStatusChoice.objects.get(name='Pending - Add')
        # project_user_status_choices['PER'] = ProjectUserStatusChoice.objects.get(name='Pending - Remove')
        # project_user_status_choices['DEN'] = ProjectUserStatusChoice.objects.get(name='Denied')
        # project_user_status_choices['REM'] = ProjectUserStatusChoice.objects.get(name='Removed')
        # project_user_status_choices['Missing'] = ProjectUserStatusChoice.objects.get(name='Removed')
        # for choice in ['Active', 'Pending Remove', 'Denied', 'Removed', ]:
        #     ProjectUserStatusChoice.objects.get_or_create(name=choice)
        
        # with open (file_path, 'r') as read_obj:
        #     csv_reader = reader(read_obj) # opt out the first line
        #     first_line = read_obj.readline()  
        #     for row in csv_reader:
        #         created = "2021-02-01   10:00:00" # feeding dummy data for now
        #         modified = "2021-03-01  10:00:00" # feeding dummy data for now
        #         title = lab_name
        #         pi_username = "shiwei" # put in my username for now
        #         description = "could I have 1 TB of data, please?"
        #         field_of_science = "other"
        #         project_status = "New"
        #         user_info = row[0] + ",PI,PI,ACT"

        #         created = datetime.datetime.strptime(created.split('.')[0], '%Y-%m-%d %H:%M:%S')
        #         modified = datetime.datetime.strptime(modified.split('.')[0], '%Y-%m-%d %H:%M:%S')

        #         try:
        #             if (row[3] == 'FACULTY'):
        #                 username = row[0]
        #                 pi_user_obj = User.objects.get(username = username)
        #         except ObjectDoesNotExist:
        #             print("could not make project because user does not exist. Please add user first")
        #             continue

        #         pi_user_obj.is_pi = True
        #         pi_user_obj.save()

        #         field_of_science_obj = FieldOfScience.objects.get(description=field_of_science)
        #         # create my project_object
        #         project_obj = Project.objects.create(
        #             created=created,
        #             modified=modified,
        #             title=title.strip(),
        #             pi=pi_user_obj,
        #             description=description.strip(),
        #             field_of_science=field_of_science_obj,
        #             status=project_status_choices[project_status]
        #         )
