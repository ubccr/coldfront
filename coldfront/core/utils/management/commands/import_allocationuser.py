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
        file_path = os.path.join(base_dir, 'local_data/holylfs04')
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
        for f in arr:
            lab = f.split(".")
            lab_name = lab[0]
        
            filtered_query = Project.objects.get(title = lab_name) # find project
            data = {} # initialize an empty dictionary
            file_path = file_path + "/" + f
            print("loading",file_path,"...")
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
                    allocation_count = Allocation.objects.count()
                    allocations = Allocation.objects.filter(project = filtered_query)
                
                except Allocation.DoesNotExist:
                    allocations, created = Allocation.objects.get_or_create(
                        project=project_obj,
                        status=AllocationStatusChoice.objects.get(name='Active'),
                        start_date=start_date,
                        end_date=end_date,
                        justification='Allocation Information for ' + lab_name
                    )
                 
            
                if (allocations.count() == 0):
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
               
                    lab_data = data[0]
                    data = data[1:] # skip the usage information
                    
                    lab_allocation, alpha = splitString(lab_data["quota"])
                    lab_allocation = float(lab_allocation)

                    lab_allocation_in_tb = kb_to_tb(lab_allocation)
                    lab_allocation_in_tb = float(lab_allocation_in_tb)
                    lab_allocation_in_tb_str = str(lab_allocation_in_tb)

                    lab_usage_in_kb =lab_data['kbytes']
                    lab_usage_in_kb = float(lab_usage_in_kb)
                    lab_usage_in_tb = kb_to_tb(lab_usage_in_kb)
                    lab_usage_in_tb = round(lab_usage_in_tb, 2)
                    lab_usage_in_tb_str = str(lab_usage_in_tb)

                    allocation = allocations[0]
                    if (allocation): # get allocation
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
                            allocation_attribute_type_obj =AllocationAttribute.objects.get_or_create(
                                allocation_attribute_type=allocation_attribute_type_obj,
                                allocation=allocation,
                                value = lab_allocation_in_tb_str) 
                         
                        else:
                            allocation_attribute_obj.value = lab_allocation_in_tb_str # this has a bug, not updating value
                        allocation_attribute_type_obj.save()
                        
                        allocation_attribute_obj.allocationattributeusage.value = lab_usage_in_tb_str
                        allocation_attribute_obj.allocationattributeusage.save()

                        allocation_users = allocation.allocationuser_set.order_by('user__username')
                    
                        user_json_dict = dict() #key: username, value paid: user_lst dictionary
                        # store every user from JSON in a dictionary
                        for user_lst in data: #user_lst is lst
                            user_json_dict[user_lst['user']] = user_lst

                        # checking my user_json_dictinary
                        # loop through my allocation_users set
                        for allocation_user in allocation_users:
                            allocation_user_username = (allocation_user.user.username)
                            
                            if allocation_user_username in user_json_dict:
                                one_user_logical_usage = user_json_dict[allocation_user_username]['logical_usage']
                                allocation_user.usage_bytes = one_user_logical_usage
                                num, alpha = splitString(user_json_dict[allocation_user_username]['usage'])
                                allocation_user.usage = num
                                allocation_user.unit = alpha
                                allocation_user.save()
                            else:
                                # if this allocation_user from web is not in JSON, I delete this allocationuser from Web
                                allocation_users.remove(allocation_user) # remove this particular allocation_user
                        
                        # import allocationuser from JSON; 
                        # if user doesn't exist: I create user object, allocationuser object
                        # if user does exist, I update allocationuser object
                        for json_user in user_json_dict:
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

            file_path = os.path.join(base_dir, 'local_data/holylfs04')
           