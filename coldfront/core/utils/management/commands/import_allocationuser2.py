import datetime
import os
import json

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import BaseCommand

from coldfront.core.allocation.models import (Allocation, AllocationAttribute,
                                              AllocationAttributeType,
                                              AllocationStatusChoice,
                                              AllocationUser,
                                              AllocationUserStatusChoice)
from coldfront.core.field_of_science.models import FieldOfScience
from coldfront.core.grant.models import (Grant, GrantFundingAgency,
                                         GrantStatusChoice)
from coldfront.core.project.models import (Project, ProjectStatusChoice,
                                           ProjectUser, ProjectUserRoleChoice,
                                           ProjectUserStatusChoice)
from coldfront.core.publication.models import Publication, PublicationSource
from coldfront.core.resource.models import (Resource, ResourceAttribute,
                                            ResourceAttributeType,
                                            ResourceType)
from coldfront.core.user.models import UserProfile

from csv import reader

base_dir = settings.BASE_DIR

def splitString(str): 
  
    alpha = "" 
    num = "" 
    special = "" 
    for i in range(len(str)): 
        if (str[i].isdigit()): 
            num = num+ str[i] 
        elif((str[i] >= 'A' and str[i] <= 'Z') or
             (str[i] >= 'a' and str[i] <= 'z')): 
            alpha += str[i] 
        else: 
            num += str[i] 
  
    return(num, alpha)

class Command(BaseCommand):

    def handle(self, *args, **options):
        lab_username_dict = {
            "zhuang_lab": "xzhuang",
            "moorcroft_lab": "prm",
            "kuang_lab": "kuang",
            "kovac_lab": "akovacs",
            "holman_lab": "mholman",
            "giribet_lab": "ggiribet",
            "edwards_lab": "sedwards",
            "denolle_lab": "mdenolle",
            "wofsy_lab": "steven_wofsy"
        }
       

        lab_name = input("Lab name is: ")
        pi1 = User.objects.get(username=lab_username_dict[lab_name])
        file_name = lab_name + '.json'
        resource_type_obj = ResourceType.objects.get(name="Storage")
        parent_resource_obj = None
        name = "holylfs04"
        description = "Service Type: Storage"
        is_available = True
        is_public = True
        is_allocatable = True

        file_name_quota = "Quota.csv" 

        Resource.objects.get_or_create(
            resource_type=resource_type_obj,
            parent_resource=parent_resource_obj,
            name=name,
            description=description,
            is_available=is_available,
            is_public=is_public,
            is_allocatable=is_allocatable
        )
        # don't create a new project (if project exist, don't create new project); otherwise, create one;
        # check get_or_create function; just do Project.objects.get();
        # lab_name = "holman_lab" # lab name: giribet_lab, kovac_lab etc
       
        # file_name = "holman_lab.json"
        file_path = os.path.join(base_dir, 'local_data', file_name)
        file_path_quota = os.path.join(base_dir, 'local_data', file_name_quota)
        print("this is my file path", file_path)
        print("quota file path is:", file_path_quota)
        # putting quota information in a dictionary
        # open file in read mode
        
        lab_allocation_usage_dict = dict() # dictionary, key is string, value is list
        with open(file_path_quota, 'r') as read_obj:
            # pass the file object to reader() to get the reader object
            csv_reader = reader(read_obj)
            first_line = read_obj.readline()  #opt out first line
            # Iterate over each row in the csv using reader object
            
            for row in csv_reader:
                lst = [] 
                # row variable is a list that represents a row in csv
                lst.append(int(row[1]))
                lst.append(float(row[2]))
                lst.append(float(row[3]))
                lab_allocation_usage_dict[row[0]] = lst

        filtered_query = Project.objects.filter(title = lab_name)
        found_project = False # set default value to false
        print(filtered_query)
        if not filtered_query:
            print("I cannot find this lab")
        else:
            print("I found this lab")
            found_project = True
        if (not found_project):
            project_obj, _ = Project.objects.get_or_create(
                pi = pi1,
                title = lab_name,
                description= lab_name + ' storage allocation',
                field_of_science=FieldOfScience.objects.get(
                    description='Other'),
                status=ProjectStatusChoice.objects.get(name='Active'),
                force_review=True
            )
            start_date = datetime.datetime.now()
            end_date = datetime.datetime.now() + relativedelta(days=365)
        else:
            project_obj = Project.objects.get(title = lab_name)
            start_date = datetime.datetime.now()
            end_date = datetime.datetime.now() + relativedelta(days=365)

        allocation_obj, _ = Allocation.objects.get_or_create(
            project=project_obj,
            status=AllocationStatusChoice.objects.get(name='Active'),
            start_date=start_date,
            end_date=end_date,
            justification='Allocation Information for ' + lab_name
        )
        allocation_obj.resources.add(
            Resource.objects.get(name='holylfs04'))
        allocation_obj.save()

#begin: input allocation usage data
        lab_allocation = lab_allocation_usage_dict[lab_name][0]
        lab_usage = lab_allocation_usage_dict[lab_name][1]
        lab_usage_in_bytes = lab_allocation_usage_dict[lab_name][2]
       
        allocation_attribute_type_obj = AllocationAttributeType.objects.get(
            name='Tier 0')

        allocation_attribute_type_obj = AllocationAttributeType.objects.get(
            name='Storage Quota (TB)')
        allocation_attribute_obj, _ = AllocationAttribute.objects.get_or_create(
            allocation_attribute_type=allocation_attribute_type_obj,
            allocation=allocation_obj,
            value=lab_allocation)

        allocation_attribute_obj.allocationattributeusage.value = lab_usage
        allocation_attribute_obj.allocationattributeusage.save()

        allocation_attribute_type_obj = AllocationAttributeType.objects.get(
            name= 'Tier 0 - $50/TB/yr')
        allocation_attribute_obj, _ = AllocationAttribute.objects.get_or_create(
            allocation_attribute_type=allocation_attribute_type_obj,
            allocation=allocation_obj,
            value='$50/TB/yr')
        # allocation_attribute_type_obj = AllocationAttributeType.objects.get(
        #     name= 'Storage Usage (bytes)')
        # allocation_attribute_obj, _ = AllocationAttribute.objects.get_or_create(
        #     allocation_attribute_type=allocation_attribute_type_obj,
        #     allocation=allocation_obj,
        #     value=lab_usage_in_bytes)
    



        # ResourceAttribute.objects.get_or_create(resource_attribute_type=ResourceAttributeType.objects.get(
        # name='quantity_default_value'), resource=Resource.objects.get(name='Budgetstorage'), value=10)
#end: input allocation usage data

        # reading in data from JSON file, adding users
        with open (file_path) as json_file:
            data = json.load(json_file)
            # print(data)
            # print(type(data))
            # print(len(data))
            # print(data[0])
            # print(type(data[0]))
            # print(data[0]['user'])
            # print(data[0]['usage'])
            # print(type(data[0]['usage']))
            allocation_group_usage_bytes = 0
            var1 = 0
            for user_lst in data: #user_lst is lst
                print(user_lst) # this is a lst
                user_query = User.objects.filter(username = user_lst['user'])
                
                
                if not user_query:
                    print("this user does not exist")
                    # thus I am creating a user object
                    fullname = user_lst['name']
                    fullname_lst = fullname.split()
                    usage_string = user_lst['usage']
                    num, alpha = splitString(usage_string) 
                    if (len(fullname_lst) > 1):
                        first_name = fullname_lst[0]
                        last_name = fullname_lst[1]
                    else:
                        first_name = fullname_lst[0]
                        last_name = "" # no last_name
                    user_obj = User.objects.create(
                        username = user_lst['user'],
                        first_name = first_name,
                        last_name = last_name,
                        email = first_name + "_" + last_name + "_NotActive@fas.edu",
                        is_active = False,
                        is_staff = True,
                        is_superuser = False,
                    )

                    allocation_user_obj = AllocationUser.objects.create(
                        allocation=allocation_obj,
                        user=User.objects.get(username=user_lst['user']),
                        status=AllocationUserStatusChoice.objects.get(name='Inactive'),
                        usage_bytes = user_lst['logical_usage'],
                        usage = num,
                        unit = alpha,
                        allocation_group_usage_bytes = lab_usage_in_bytes,
                       
                    )
                    User.objects.get(username=user_lst['user']).save()
                    allocation_user_obj.save()
                else:
                    print(user_lst['user'], "exists")
                    usage_string = user_lst['usage']
                    num, alpha = splitString(usage_string) 
                    # load allocation user
                  
                    allocation_user_obj = AllocationUser.objects.create(
                        allocation=allocation_obj,
                        user=User.objects.get(username=user_lst['user']),
                        status=AllocationUserStatusChoice.objects.get(name='Active'),
                        usage_bytes = user_lst['logical_usage'],
                        usage = num,
                        unit = alpha,
        
                        allocation_group_usage_bytes = lab_usage_in_bytes,
                        
                    )
                
                    print("line255", var1)
                    User.objects.get(username=user_lst['user']).save()
                    allocation_user_obj.save()
                print("line251", allocation_user_obj.allocation_group_usage_bytes)
            print("line261", allocation_user_obj.allocation_group_usage_bytes)

        

