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
        filtered_query = Project.objects.get(title = lab_name)
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
            allocations = Allocation.objects.filter(project = filtered_query)
            print("allocations is**", allocations)
            lab_data = data[0]
            data = data[1:] # skip the usage information
            
            print("lab_data is", lab_data)
            print("type of lab_data is", type(lab_data))

            lab_allocation, alpha = splitString(lab_data["quota"])
            lab_allocation = float(lab_allocation)
            print("lab_allocation is", lab_allocation)

            lab_allocation_in_tb = kb_to_tb(lab_allocation)
            lab_allocation_in_tb = float(lab_allocation_in_tb)
            print("lab_allocation in tb is", lab_allocation_in_tb)

            lab_usage_in_kb = lab_data['kbytes'] 
            lab_usage_in_kb = float(lab_usage_in_kb)
            lab_usage_in_tb = kb_to_tb(lab_usage_in_kb)
            print("lab_usage_in_kb is", lab_usage_in_kb)
            print("lab_usage_in_tb is", lab_usage_in_tb)

            allocation = allocations[0]
            print("line 149", allocation, type(allocation))
            allocation_attribute_type_obj = AllocationAttributeType.objects.get_or_create(
                name='Tier 0')
            allocation_attribute_type_obj = AllocationAttributeType.objects.get_or_create(
                name='Storage Quota (TB)')
            allocation_attribute_obj, _ = AllocationAttribute.objects.get_or_create(
                allocation_attribute_type=allocation_attribute_type_obj,
                allocation=allocation,
                value="2000")

            allocation_usage = kb_to_tb(float(lab_data["kbytes"]))
            allocation_attribute_obj.allocationattributeusage.value = kb_to_tb(float(lab_data["kbytes"]))
            allocation_attribute_obj.allocationattributeusage.save()
