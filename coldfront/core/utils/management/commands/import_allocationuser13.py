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
    
def kb_to_tb(kb_storage):
    tb_storage = kb_storage / 1073741824
    return tb_storage

def kb_to_bytes(kb_storage):
    tb_storage = kb_storage * 1024
    return tb_storage

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
            "wofsy_lab": "steven_wofsy",
            "arguelles_delgado_lab": "carguelles",
            "balazs_lab": "abalazs",
            "barak_lab": "bbarak",
            "beam_lab":"abeam",
            "berger_lab":"berger",
            "bhi": "aloeb",
            "brownfield_lab": "dbrownfield"
        }
        
        file_path = os.path.join(base_dir, 'local_data')
        labs = ["holylfs04"]
        lab_name = 'giribet_lab.json'
        lab_name = lab_name.split(".")
        print("lab_name is:", lab_name)
        pi1 = User.objects.get(username=lab_username_dict[lab_name[0]])
        file_name = lab_name[0] + '.json'
        print("file_name is:", file_name)
        resource_type_obj = ResourceType.objects.get(name="Storage")
        parent_resource_obj = None
        name = "holylfs04/tier0" # making getting the name dynamic from the .json file
        description = "Service Type: Storage"
        is_available = True
        is_public = True
        is_allocatable = True

        obj, created = Resource.objects.get_or_create(
            resource_type=resource_type_obj,
            parent_resource=parent_resource_obj,
            name=name,
            description=description,
            is_available=is_available,
            is_public=is_public,
            is_allocatable=is_allocatable
        )

        file_path = '/Users/Shiwei/Desktop/coldfront_apps/coldfront/local_data/holylfs04/giribet_lab.json'
        print("line 114 file_path is", file_path)

        lab_name = 'giribet_lab'
        filtered_query = Project.objects.get(title = lab_name) # find project
        print("filtered_query is", filtered_query)
        data = {} # initialize an empty dictionary

        with open(file_path) as f:
            data = json.load(f)

        if (not filtered_query): # if not found project, then create project
            print("if statement")
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

        else: # found project
            print("else statement")
            print("filtered_query is", filtered_query)
            allocations = Allocation.objects.filter(project = filtered_query)
            print("allocations is**", allocations)
            if (not allocations.exists()): # under my project there are no allocations
                print("my allocations queryset is empty")
                project_obj = Project.objects.get(title = lab_name)
                start_date = datetime.datetime.now()
                end_date = datetime.datetime.now() + relativedelta(days=365)
                # import allocations
                allocation_obj, _ = Allocation.objects.get_or_create(
                    project=project_obj,
                    status=AllocationStatusChoice.objects.get(name='Active'),
                    start_date=start_date,
                    end_date=end_date,
                    justification='Allocation Information for ' + lab_name
                )
                allocation_obj.resources.add(
                    Resource.objects.get(name='holystore01/tier0'))
                allocation_obj.save()
                # import allocation user and user info
            else: # under project I found this specific allocation
                lab_data = data[0]
                data = data[1:] # skip the usage information
                
                print("lab_data is", lab_data)
                print("type of lab_data is", type(lab_data))
                print("data is", data)
                print("type of data is", type(data))

                lab_allocation, alpha = splitString(lab_data["quota"])
                lab_allocation = float(lab_allocation)
                print("lab_allocation in kb is", lab_allocation)

                lab_allocation_in_tb = kb_to_tb(lab_allocation)
                lab_allocation_in_tb = float(lab_allocation_in_tb)
                print("lab_allocation in tb is", lab_allocation_in_tb)

                lab_usage_in_kb =lab_data['kbytes']
                lab_usage_in_kb = float(lab_usage_in_kb)
                lab_usage_in_tb = kb_to_tb(lab_usage_in_kb)
                print("lab_usage_in_kb is", lab_usage_in_kb)
                print("lab_usage_in_tb is", lab_usage_in_tb)

                allocation = allocations[0]
                print("line 149", allocation, type(allocation))
               
                if (allocation): # get allocation
                    print("line 170: allocation object exists")
                    allocation_users = allocation.allocationuser_set.order_by('user__username')
                    print("I got my allocation, here is my allocation_users set", allocation_users)
                    print(type(allocation_users))

                    user_json_dict = dict() #key: username, value paid: user_lst dictionary
                    # store every user from JSON in a dictionary
                    for user_lst in data: #user_lst is lst
                        print("user_lst is", user_lst)
                        print("type of user_lst", type(user_lst))
                        print("user_lst's username", user_lst['user']) #username
                        user_json_dict[user_lst['user']] = user_lst

                    # checking my user_json_dictinary
                    print("my user_json_dict is", user_json_dict)
                    # loop through my allocation_users set
                    for allocation_user in allocation_users:
                        allocation_user_username = (allocation_user.user.username)
                        print('1 users username is', allocation_user_username)
                        
                        if allocation_user_username in user_json_dict:
                            print(type(allocation_user_username))
                            print(allocation_user_username, "is in JSON, thus I only need to update userinfo from JSON")
                            one_user_logical_usage = user_json_dict[allocation_user_username]['logical_usage']
                            print(allocation_user_username,'kbytes usage is', one_user_logical_usage)
                            allocation_user.usage_bytes = one_user_logical_usage
                            num, alpha = splitString(user_json_dict[allocation_user_username]['usage'])
                            allocation_user.usage = num
                            allocation_user.unit = alpha
                            allocation_user.save()
                        else:
                            print(type(allocation_user_username))
                            print(allocation_user_username, "is not in JSON")
                            # if this allocation_user from web is not in JSON, I delete this allocationuser from Web
                            allocation_users.remove(allocation_user) # remove this particular allocation_user
                    
                    # import allocationuser from JSON; 
                    # if user doesn't exist: I create user object, allocationuser object
                    # if user does exist, I update allocationuser object
                    for json_user in user_json_dict:
                        print("json_user is",json_user)
                        print("type(json_user) is",type(json_user))
                        print("user_json_dict[json_user] is", user_json_dict[json_user], type(user_json_dict[json_user]))
                        print(allocation_users)
                        print(type(allocation_users))
                        print("looping through JSON file")
                        # if JSON allocationuser is not in user: create user; create allocation user
                        # if JSON allocationuser is in user, check 
                        """
                        if user yes AllocationUser yes: then update allocationuser
                        if user yes AllocationUser no: then create allocationuser
                        if user no allocationuser no: create both
                        if user no allocationuser yes: this scenario does not exist
                        """
                        # check whether user is in User object
                        user_exist = False
                        allocation_user_exist = False
                        try: 
                            user_obj = User.objects.get(username = json_user)
                            user_exist = True
                        except User.DoesNotExist:
                            user_exist = False
                        
                        try: 
                            allocationuser_obj = AllocationUser.objects.get(user=user_obj)
                            print("line254, allocationuser_obj", allocationuser_obj, type(allocationuser_obj))
                            allocation_user_exist = True
                        except AllocationUser.DoesNotExist:
                            allocation_user_exist = False



                        if (not user_exist):
                            # create user object
                            fullname = user_json_dict[json_user]['name']
                            fullname_lst = fullname.split()
                            if (len(fullname_lst) > 1):
                                first_name = fullname_lst[0]
                                last_name = fullname_lst[1]
                            else:
                                first_name = fullname_lst[0]
                                last_name = "" # no last_name
                            user_obj = User.objects.create(
                                username = json_user,
                                first_name = first_name,
                                last_name = last_name,
                                email = "Not_Active@fas.edu",
                                is_active = False,
                                is_staff = False,
                                is_superuser = False,
                            )
                            User.objects.get(username=json_user).save()
                        
                        
                        print("this is my allocationuser:", )

                   
                        if (not allocation_user_exist):
                            print("line263")
                            # create allocationuser object
                            usage_string = user_json_dict[json_user]['usage']
                            num, alpha = splitString(usage_string)
                            allocation_user_obj = AllocationUser.objects.create(
                                allocation=allocation,
                                user=user_obj,
                                status=AllocationUserStatusChoice.objects.get(name='Inactive'),
                                usage_bytes = user_json_dict[json_user]['logical_usage'],
                                usage = num,
                                unit = alpha,
                                allocation_group_quota = lab_data["quota"],
                                allocation_group_usage_bytes = lab_data["kbytes"],
                            )
                            allocation_user_obj.save()

                        if (allocation_user_exist):
                            print("line280")
                            # only updating allocation user object
                            usage_string = user_json_dict[json_user]['usage']
                            num, alpha = splitString(usage_string)
                            print("line256 num is", num)
                            allocationuser_obj.usage = num
                            allocationuser_obj.usage_bytes = user_json_dict[json_user]['logical_usage']
                            allocationuser_obj.unit = alpha
                            allocationuser_obj.allocation_group_usage_bytes = lab_data["kbytes"]
                            allocationuser_obj.allocation_group_quota = lab_data["quota"]
                            allocationuser_obj.save()
                            User.objects.get(username=json_user).save()

