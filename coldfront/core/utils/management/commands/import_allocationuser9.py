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

        # labs = ["holystore01_copy", "holylfs04"]
        for lab in labs:
            print("lab is", lab)
            lab_path = 'local_data/' + lab 
            file_path = os.path.join(base_dir, lab_path)
            arr = os.listdir(file_path)
            lab_list = []
            
            for f in arr:
                f_name = f.split('.')
                if (f_name[len(f_name)-1] == 'json'):
                    my_file = f_name[len(f_name)-2]+('.json')
                    lab_list.append(my_file)
            print("lab_list is", lab_list)
            for lab_name in lab_list:
                lab_json_file = lab_name
            # lab_name = 'giribet_lab.json'
                lab_name = lab_name.split(".")
                print("lab_name is:", lab_name)
                pi1 = User.objects.get(username=lab_username_dict[lab_name[0]])
                file_name = lab_name[0] + '.json'
                print("file_name is:", file_name)
                resource_type_obj = ResourceType.objects.get(name="Storage")
                parent_resource_obj = None
                name = lab+"/tier0" # making getting the name dynamic from the .json file
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
               
                file_path = os.path.join(base_dir, lab_path, file_name)
                file_path = '/Users/Shiwei/Desktop/coldfront_apps/coldfront/local_data/holylfs04/'+lab_json_file
                print("line 114 file_path is", file_path)
                
                lab_allocation_usage_dict = dict()
                data = {} # initialize an empty dictionary
                with open(file_path) as f:
                    data = json.load(f)
                
                lab_name = lab_name[0]
                filtered_query = Project.objects.get(title = lab_name)
                print("filtered_query is", filtered_query)
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
                    allocations = Allocation.objects.filter(project = filtered_query)
                    print("allocations is**", allocations)
                    lab_data = data[0]
                    data = data[1:] # skip the usage information
                    
                    print("lab_data is", lab_data)
                    print("data is", data)
                    for user_lst in data: #user_lst is lst
                        print("user_lst is", user_lst)
                        for allocation in allocations:
                            print("allocation is@", allocation)
                            allocation_users = allocation.allocationuser_set.order_by('user__username')
                            print("allocation_users is", allocation_users)
                            if not allocation_users.exists():
                                print("allocationuser query set is empty")
                                print(type(data))
                                print("data is", data)
                                print(data[0])
                                print(data[1])
                                print(data[2])
                                print("line157",type(data[0]))
                                for user_lst in data:
                                    print(user_lst)
                                    fullname = user_lst['name']
                                    fullname_lst = fullname.split()
                                    usage_string = user_lst['usage']
                                    num, alpha = splitString(usage_string) 
                                    print("line 164 num, alpha is", num, alpha)
                                    lab_allocation, alpha = splitString(lab_data["quota"])
                                    lab_allocation = float(lab_allocation)
                                    lab_usage_in_bytes = lab_data['kbytes'] 
                                    lab_usage_in_bytes = float(lab_usage_in_bytes )* 1024

                                    allocation_attribute_type_obj = AllocationAttributeType.objects.get_or_create(
                                        name='Tier 0')
                                    allocation_attribute_type_obj = AllocationAttributeType.objects.get_or_create(
                                        name='Storage Quota (TB)')
                                    allocation_attribute_obj, _ = AllocationAttribute.objects.get_or_create(
                                        allocation_attribute_type=allocation_attribute_type_obj,
                                        allocation=allocation,
                                        value=lab_allocation)
                                    allocation_usage, allocation_usage_unit = splitString(lab_data["kbytes"])
                                
                                    # lab_usage, alpha_usage = splitString(lab_data["kbytes"])
                                    # lab_usage = float(lab_usage)
                                    # if (alpha_usage == 'T'):
                                    #     lab_usage_in_bytes = lab_usage * 1099511627776
                                    # if (alpha_usage == 'G'):
                                    #     lab_usage_in_bytes = lab_usage * 1073741824
                                    # if (alpha_usage == 'M'):
                                    #     lab_usage_in_bytes = lab_usage * 1048576
                                    allocation_user_obj = AllocationUser.objects.create(
                                        allocation=allocation,
                                        user=User.objects.get(username=user_lst['user']),
                                        status=AllocationUserStatusChoice.objects.get(name='Active'),
                                        usage_bytes = user_lst['logical_usage'],
                                        usage = num,
                                        unit = alpha,
                                        allocation_group_quota = lab_allocation,
                                        allocation_group_usage_bytes = lab_usage_in_bytes,
                                    )
                                    User.objects.get(username=user_lst['user']).save()
                                    allocation_user_obj.save()

                            else: #loop through the query set and updating user's usage
                                print("else, loop through the query set and updating user's usage")
                                
                                # allocation_users = allocation.allocationuser_set.exclude(status__name__in=['Removed']).order_by('user__username')
                                for allocation_user in allocation_users: # loop through allocation_user set
                                    print("********** line 150 **********")
                                    if (allocation_user.user.username == user_lst['user']): # updating allocation user
                                        print("line151 if statement")
                                        usage_string = user_lst['usage']
                                        num, alpha = splitString(usage_string)
                                        allocation_user.usage = num
                                        allocation_user.usage_bytes = user_lst['logical_usage']
                                        allocation_user.unit = alpha
                                        allocation_user.save()
                           
                     
                        # if (allocation_user): # create allocation user
                        #     print("line159 else statement")
                        #     usage_string = user_lst['usage']
                        #     num, alpha = splitString(usage_string)
                        #     allocation_user_obj = AllocationUser.objects.create(
                        #     allocation=allocation_obj,
                        #     user=User.objects.get(username=user_lst['user']),
                        #     status=AllocationUserStatusChoice.objects.get(name='Active'),
                        #     usage_bytes = user_lst['logical_usage'],
                        #     usage = num,
                        #     unit = alpha,
                        #     # allocation_group_quota = lab_allocation,
                        #     # allocation_group_usage_bytes = lab_usage_in_bytes,
                        # )
                        # User.objects.get(username=user_lst['user']).save()
                        # allocation_user_obj.save()
