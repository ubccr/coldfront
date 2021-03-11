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
        pi1 = User.objects.get(username='xzhuang')
        user1 = User.objects.get(username='shiwei')
        resource_type_obj = ResourceType.objects.get(name="Storage")
        parent_resource_obj = None
        name = "FAS RC"
        description = "FAS RC Research Computing"
        is_available = True
        is_public = True
        is_allocatable = True

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
        lab_name = input("lab name is:")
        file_name = lab_name + '.json'
        # file_name = "holman_lab.json"
        file_path = os.path.join(base_dir, 'local_data', file_name)
        print("this is my file path", file_path)

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
                description= lab_name + ' test description',
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
            justification='Test justification reasoning.'
        )
        allocation_obj.resources.add(
            Resource.objects.get(name='FAS RC'))
        allocation_obj.save()

        # reading in data from JSON file, adding users
        with open (file_path) as json_file:
            data = json.load(json_file)
            print("line88")
            print(data)
            print("line89")
            print(type(data))
            print("line89.1")
            print(len(data))
            print("line90")
            print(data[0])
            print("line96")
            print(type(data[0]))
            print(data[0]['user'])
            print("line99")
            print("line111")
            print(data[0]['usage'])
            print(type(data[0]['usage']))
            
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
                        email = first_name + "_" + last_name + "NotActive@fas.edu",
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
                        unit = alpha
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
                        unit = alpha
                    )
                    User.objects.get(username=user_lst['user']).save()
                    allocation_user_obj.save()
        
        

