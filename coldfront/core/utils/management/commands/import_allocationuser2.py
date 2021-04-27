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
from coldfront.config.env import ENV

from csv import reader
from os import walk

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

        LOCALDATA_ROOT = ENV.str('LOCALDATA_ROOT', default= base_dir)
        # file_path = './local_data/holylfs04/giribet_lab.json'
        file_path = os.path.join(base_dir, 'local_data/holylfs04')
        print("file_path is", file_path)
        labs = ["holylfs04"]
        lab_names = ['']
        lab_name = 'giribet_lab.json'
        lab_name = lab_name.split(".")
        pi1 = User.objects.get(username=lab_username_dict[lab_name[0]])
        file_name = lab_name[0] + '.json'
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
        arr = os.listdir(file_path)
        print("line107, arr is", arr)
        # file_path = '/Users/Shiwei/Desktop/coldfront_apps/coldfront/local_data/holylfs04/giribet_lab.json'
        for f in arr:
            lab = f.split(".")
            lab_name = lab[0]
        
            filtered_query = Project.objects.get(title = lab_name) # find project
            print("line114, filtered_query", filtered_query)
            data = {} # initialize an empty dictionary
            file_path = file_path + "/" + f
            print(file_path, "this is my file_path")
            with open(file_path) as f:
                data = json.load(f)

            if (not filtered_query): # if not found project, then create project
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
                try:
                    print("line136 try statement")
                    allocation_count = Allocation.objects.count()
                    allocations = Allocation.objects.filter(project = filtered_query)
                    # allocations.resources.add(
                    #     Resource.objects.get(name='holystore01/tier0'))
                    # allocations.save()
                except Allocation.DoesNotExist:
                    print("line143 except statement")
                    allocations, created = Allocation.objects.get_or_create(
                        project=project_obj,
                        status=AllocationStatusChoice.objects.get(name='Active'),
                        start_date=start_date,
                        end_date=end_date,
                        justification='Allocation Information for ' + lab_name
                    )
                    # allocations.resources.add(
                    #     Resource.objects.get(name='holystore01/tier0'))
                    # allocations.save()
                print("line154, allocations",allocations)
                print("line155", type(allocations))
                if (allocations.count() == 0):
                # if (not allocations.exists()): # under my project there are no allocations
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
                        Resource.objects.get(name='holylfs04/tier0'))
                    allocation_obj.save()
                    # import allocation user and user info
                if (allocation_count >= 1):
                # else: # under project I found this specific allocation
                # if (allocation_count >= 1):
                    lab_data = data[0]
                    data = data[1:] # skip the usage information
                    
                    lab_allocation, alpha = splitString(lab_data["quota"])
                    lab_allocation = float(lab_allocation)
                    print("line 173 lab_allocation, alpha", lab_allocation, "|", alpha)

                    lab_allocation_in_tb = kb_to_tb(lab_allocation)
                    lab_allocation_in_tb = float(lab_allocation_in_tb)
                    print("line 177 lab_allocation_in_tb, alpha", lab_allocation_in_tb)
                    lab_allocation_in_tb_str = str(lab_allocation_in_tb)
                    print("line179", lab_allocation_in_tb_str, type(lab_allocation_in_tb_str))

                    lab_usage_in_kb =lab_data['kbytes']
                    lab_usage_in_kb = float(lab_usage_in_kb)
                    lab_usage_in_tb = kb_to_tb(lab_usage_in_kb)
                    lab_usage_in_tb = round(lab_usage_in_tb, 2)
                    lab_usage_in_tb_str = str(lab_usage_in_tb)
                    print("line185", lab_usage_in_tb_str)
                    print("line194, allocations",allocations)

                    allocation = allocations[0]
                    if (allocation): # get allocation
                        # lab_allocation, alpha = splitString(data[0]["quota"])
                        # lab_allocation = float(lab_allocation)
                        # lab_usage, alpha_usage = splitString(data[0]["kbytes"])
                        # lab_usage = float(lab_usage)
                        # if (alpha_usage == 'T'):
                        #     lab_usage_in_bytes = lab_usage * 1099511627776
                        # if (alpha_usage == 'G'):
                        #     lab_usage_in_bytes = lab_usage * 1073741824
                        # allocation_attribute_type_obj = AllocationAttributeType.objects.get(
                        #     name='Tier 0')
                        allocation_attribute_type_obj = AllocationAttributeType.objects.get(
                            name='Storage Quota (TB)')

                        try:
                            allocation_attribute_obj = AllocationAttribute.objects.get(
                                allocation_attribute_type=allocation_attribute_type_obj,
                                allocation=allocation,
                            )
                            allocation_attribute_exist = True
                        except AllocationAttribute.DoesNotExist:
                            allocation_attribute_exist = False
                            
                        if (not allocation_attribute_exist):
                            print("if statement")
                            allocation_attribute_type_obj =AllocationAttribute.objects.get_or_create(
                                allocation_attribute_type=allocation_attribute_type_obj,
                                allocation=allocation,
                                value = lab_allocation_in_tb_str) 
                            # allocation_attribute_type_obj.save()
                        else:
                            print("else statement")
                            # allocation_attribute_obj.value = '181' # this has a bug, not updating value
                            allocation_attribute_obj.value = lab_allocation_in_tb_str # this has a bug, not updating value
                        allocation_attribute_type_obj.save()

                        # allocation_usage, allocation_usage_unit = splitString(data[0]["kbytes"])
                        # if (allocation_usage_unit == 'G'):
                        #     lab_usage_in_TB = lab_usage // 1073741824
                        # if (allocation_usage_unit == 'M'):
                        #     lab_usage_in_TB = lab_usage // 1048576
                        # allocation_attribute_obj.allocationattributeusage.value = '81'
                        
                        allocation_attribute_obj.allocationattributeusage.value = lab_usage_in_tb_str
                        # allocation_attribute_obj.allocationattributeusage.value = allocation_usage
                        allocation_attribute_obj.allocationattributeusage.save()
                        print("line dru 236", allocation_attribute_obj.value)

                        # allocation_attribute_type_obj = AllocationAttributeType.objects.get(
                        #     name= 'Tier 0 - $50/TB/yr')
                        # allocation_attribute_obj, _ = AllocationAttribute.objects.get_or_create(
                        #     allocation_attribute_type=allocation_attribute_type_obj,
                        #     allocation=allocation,
                        #     value='$50/TB/yr')

                        
                        allocation_users = allocation.allocationuser_set.order_by('user__username')
                    
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
                                print("line304", user_obj)
                                user_exist = True
                            except User.DoesNotExist:
                                print("line307 User.DoesNotExist")
                                user_exist = False

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
                            
                            
                            try: 
                                allocationuser_obj = AllocationUser.objects.get(user=user_obj)
                                allocation_user_exist = True
                            except AllocationUser.DoesNotExist:
                                allocation_user_exist = False

                    
                            if (not allocation_user_exist):
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
                                # only updating allocation user object
                                usage_string = user_json_dict[json_user]['usage']
                                num, alpha = splitString(usage_string)
                                allocationuser_obj.usage = num
                                allocationuser_obj.usage_bytes = user_json_dict[json_user]['logical_usage']
                                allocationuser_obj.unit = alpha
                                allocationuser_obj.allocation_group_usage_bytes = lab_data["kbytes"]
                                allocationuser_obj.allocation_group_quota = lab_data["quota"]
                                allocationuser_obj.save()
                                User.objects.get(username=json_user).save()

                        print("line dru 364", allocation_attribute_obj.value)
            file_path = os.path.join(base_dir, 'local_data/holylfs04')
           