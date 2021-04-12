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
        print("file_path is", file_path)

        labs = ["holystore01_copy", "holylfs04"]
        for lab in labs:
            lab_path = 'local_data/' + lab 
            file_path = os.path.join(base_dir, lab_path)
            arr = os.listdir(file_path)
            print("line96 arr is", arr)
            print("line96 filepath is", file_path)
            lab_list = []
            for f in arr:
                f_name = f.split('.')
                if (f_name[len(f_name)-1] == 'json'):
                    my_file = f_name[len(f_name)-2]+('.json')
                    lab_list.append(my_file)
            
            print("line 91: lab_list", lab_list)

            for lab_name in lab_list:
                print("line94 lab_name:", lab_name)
                lab_name = lab_name.split(".")
                pi1 = User.objects.get(username=lab_username_dict[lab_name[0]])
                file_name = lab_name[0] + '.json'
                resource_type_obj = ResourceType.objects.get(name="Storage")
                parent_resource_obj = None
                name = lab+"/tier0" # making getting the name dynamic from the .json file
                description = "Service Type: Storage"
                is_available = True
                is_public = True
                is_allocatable = True

                # see whether this project resource needs to be created
                # where object is the retrieved or created object 
                # and created is a boolean specifying whether a new object was created
                obj, created = Resource.objects.get_or_create(
                    resource_type=resource_type_obj,
                    parent_resource=parent_resource_obj,
                    name=name,
                    description=description,
                    is_available=is_available,
                    is_public=is_public,
                    is_allocatable=is_allocatable
                )
                print("testing get_or_create")
                print(obj, created)

                file_path = os.path.join(base_dir, lab_path, file_name)
                print("this is my file path", file_path)
                
                lab_allocation_usage_dict = dict()
                data = {} # initialize an empty dictionary
                with open(file_path) as f:
                    data = json.load(f)
                    print("line 137: data is", data)
                
                lab_name = lab_name[0]
                print("line 146 lab_name is:",lab_name)
                filtered_query = Project.objects.filter(title = lab_name)
                found_project = False # set default value to false
                print("line 130, filtered query is", filtered_query)
                print(filtered_query)
                if not filtered_query:
                    print("I cannot find this lab")
                else:
                    print("I found this lab")
                    found_project = True
                if (not found_project): # if not found project, then create project
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
                    print("line 149", project_obj, _)
                else: # if I found this project, I need to find this projects allocation
                    # then I need to update allocationUser step by step
                    print("line 152 else statement")
                    project_obj = Project.objects.get(title = lab_name)
                    start_date = datetime.datetime.now()
                    end_date = datetime.datetime.now() + relativedelta(days=365)

                    allocations = Allocation.objects.filter(project = project_obj)
                    # allocations = Allocation.objects.prefetch_related(
                    # 'resources').filter(project=self.object)
                    print("line158", allocations)
                    # allocation_obj, _ = Allocation.objects.get_or_create()
                    # if (project_obj.filter.exist():) # then update
                    # AllocationO
                print("line171", lab_name)
                print("line172", type(lab_name))