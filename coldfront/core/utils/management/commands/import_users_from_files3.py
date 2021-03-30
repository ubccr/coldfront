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
from coldfront.core.allocation.models import (AllocationUser,
                                              AllocationUserStatusChoice)
from coldfront.config.env import ENV, PROJECT_ROOT

base_dir = settings.BASE_DIR


class Command(BaseCommand):

    def handle(self, *args, **options):
        print('Adding users now ...')
        # lab_list = ['zhuang_lab.csv', 'moorcroft_lab.csv', 'kuang_lab.csv', 'kovac_lab.csv',
        # 'holman_lab.csv', 'giribet_lab.csv', 'edwards_lab.csv', 'denolle_lab.csv',
        # 'wofsy_lab.csv', 'rc_admin.csv']

        local_path = os.path.join(base_dir, 'local_data')
       
        files = os.listdir(local_path)
       
        lab_list = []
        for f in files:
            f_name = f.split('.')
            if (f_name[len(f_name)-1] == 'csv'):
                if f_name[len(f_name)-2] != 'Quota':
                    print("line39:",f_name[len(f_name)-2])
                    file = f_name[len(f_name)-2]+('.csv')
                    lab_list.append(file)
            
        print(lab_list)
        for lab in lab_list:
            file_name = lab
            lab_list = list(lab.split('.'))
            lab_name = lab_list[0]
            file_path = os.path.join(base_dir, 'local_data', file_name)
            print("line34 file_name is:", file_name)
            if (file_name != "rc_admin.csv"):
                # open file in read mode
                with open (file_path, 'r') as read_obj:
                    csv_reader = reader(read_obj) # opt out the first line
                    first_line = read_obj.readline()  
                    for row in csv_reader:
                        try:
                            username = row[0]
                            user = User.objects.get(username=username)
                            #(username, "already exist, don't add to database")
                            # if the user exists, I only need to append this existing user's group
                            if not user.groups.filter(name = lab_name).exists():
                                # print("line 45",lab_name)
                                my_group = Group.objects.get(name=lab_name)
                                my_group.user_set.add(user)
                                # print ("user do not exist in", lab_name)
                            continue
                        # the type of row is 
                        except ObjectDoesNotExist:
                        
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
                            groups = lab_name 

                            # creates my user object to load data from csv to GUI
                            # create user object
                            group_objs = []
                            for group in groups.split(','):
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
                print('Finished adding users for lab:', lab)
            else:
                with open (file_path, 'r') as read_obj:
                    csv_reader = reader(read_obj) # opt out the first line
                    first_line = read_obj.readline()  
                    for row in csv_reader:
                        print("line101 row is:", row)
                        try:
                            username = row[0]
                            user, created = User.objects.get_or_create(username=username)
                            #(username, "already exist, don't add to database")
                            # if the user exists, I only need to append this existing user's group
                            if not user.groups.filter(name = lab_name).exists():
                                print("line 45",lab_name)
                                my_group = Group.objects.get(name=lab_name)
                                my_group.user_set.add(user)
                                print ("user do not exist in", lab_name)
                            print("line112, created is", created)
                            print("line113, user is:", user)
                            if not created:
                                #user was retrieved
                                username = row[0]
                                User.objects.filter(username=username).update(is_superuser=True, is_staff=True)
                            
                            continue
                        # the type of row is 
                        except ObjectDoesNotExist:
                            print("never get to except in line 137")
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
                            is_staff = True
                            is_superuser = True
                            groups = lab_name 

                            # creates my user object to load data from csv to GUI
                            # create user object
                            group_objs = []
                            for group in groups.split(','):
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
                print('Finished adding users for lab:', lab)
