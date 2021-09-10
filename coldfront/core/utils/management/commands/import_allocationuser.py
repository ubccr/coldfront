import datetime
import os
import json
import logging

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth import get_user, get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand

from coldfront.core.allocation.models import (Allocation, AllocationAttribute,
                                              AllocationAttributeType,
                                              AllocationStatusChoice,
                                              AllocationUser,
                                              AllocationUserStatusChoice)
from coldfront.core.field_of_science.models import FieldOfScience
from coldfront.core.project.models import (Project, ProjectStatusChoice)
from coldfront.core.resource.models import (Resource, )
from coldfront.config.env import ENV

from csv import reader
from os import walk

logger = logging.getLogger()

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
    help = "./manage.py import_allocationuser --storagename '' --tier ''"
    def add_arguments(self, parser):
        parser.add_argument(
            '--storagename',
            dest='stoage',
            default='holylfs04',
            help='JSON for which server ',
        )
        parser.add_argument(
            '--tier',
            dest='storagetier',
            default='tier0',
            help='Storage tier',
        )
    
    def handle(self, *args, **options):

        LOCALDATA_ROOT = ENV.str('LOCALDATA_ROOT', default=base_dir)
        storage = options['stoage'] 
        tier = options['storagetier']  
        resource_name = storage + '/' + tier
        print("Loading data for: " + resource_name)
        file_path = os.path.join(LOCALDATA_ROOT, 'local_data/',storage)
        arr = os.listdir(file_path)
        for f in arr:
            try:
                lab = f.split(".")
                lab_name = lab[0]
                print("Loading LAB: " +lab_name)
                try:
                    filtered_query = Project.objects.get(title = lab_name) # find project
                except Project.DoesNotExist:
                    # raise Exception(f'Cannot find project {lab_name}')
                    print("Project not found")
                    continue

                data = {} # initialize an empty dictionary
                lab_data = file_path + "/" + f
                with open(lab_data) as f:
                    data = json.load(f)

                # if (not filtered_query): # if not found project, then create project
                #     project_obj, _ = Project.objects.get_or_create(
                #         #pi = pi1,
                #         title = lab_name,
                #         description= lab_name + ' storage allocation',
                #         field_of_science=FieldOfScience.objects.get(
                #             #FIXME: Description of the DEPT
                #             description='Other'),
                #         status=ProjectStatusChoice.objects.get(name='Active'),
                #         force_review=True
                #     )
                #     start_date = datetime.datetime.now()
                #     end_date = datetime.datetime.now() + relativedelta(days=365)

                # else: # found project
                allocations = Allocation.objects.filter(project = filtered_query, resources__name=resource_name, status__name='Active')
                if(allocations.count() == 0):
                    print("creating allocation" + lab_name)
                    project_obj = Project.objects.get(title = lab_name)
                    if (project_obj != ""):
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
                            Resource.objects.get(name=resource_name))
                        allocation_obj.save()
                        allocations = Allocation.objects.filter(project = filtered_query,resources__name=resource_name, status__name='Active')
                
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
                # lab_usage_in_tb_str = str(lab_usage_in_tb)
                allocation= allocations[0]
                if (allocation): # get allocation
                    allocation_attribute_type_obj = AllocationAttributeType.objects.get(
                        name='Storage Quota (TB)')
                    try:
                        allocation_attribute_obj = AllocationAttribute.objects.get(
                            allocation_attribute_type=allocation_attribute_type_obj,
                            allocation=allocation,
                        )
                        allocation_attribute_obj.value = lab_allocation_in_tb_str
                        allocation_attribute_obj.save()
                        allocation_attribute_exist = True
                    except AllocationAttribute.DoesNotExist:
                        allocation_attribute_exist = False

                    if (not allocation_attribute_exist):
                        allocation_attribute_obj,_ =AllocationAttribute.objects.get_or_create(
                            allocation_attribute_type=allocation_attribute_type_obj,
                            allocation=allocation,
                            value = lab_allocation_in_tb_str)
                        allocation_attribute_type_obj.save()
                    

                    allocation_attribute_obj.allocationattributeusage.value = lab_usage_in_tb
                    allocation_attribute_obj.allocationattributeusage.save()
                    allocation_users = allocation.allocationuser_set.filter(status__name='Active').order_by('user__username')

                    user_json_dict = dict() #key: username, value paid: user_lst dictionary
                    # store every user from JSON in a dictionary
                    for user_lst in data: #user_lst is lst
                        user_json_dict[user_lst['user']] = user_lst
                        
                    # checking my user_json_dictinary
                    # loop through my allocation_users set
                    for allocation_user in allocation_users:
                        allocation_user_username = (allocation_user.user.username)
                        if allocation_user_username in user_json_dict:
                            user_obj = get_user_model().objects.get(username = allocation_user_username)
                            allocationuser_obj = AllocationUser.objects.get(user=user_obj)
                            allocationuser_obj.status = AllocationUserStatusChoice.objects.get(name='Active')
                            one_user_logical_usage = user_json_dict[allocation_user_username]['logical_usage']
                            allocationuser_obj.usage_bytes = one_user_logical_usage
                            num, alpha = splitString(user_json_dict[allocation_user_username]['usage'])
                            allocationuser_obj.usage = num
                            allocationuser_obj.unit = alpha
                            allocationuser_obj.save()
                            allocation.save()
                            user_json_dict.pop(allocation_user_username)
                        else:
                            try:
                                user_obj = get_user_model().objects.get(username = allocation_user_username)
                                allocationuser_obj = AllocationUser.objects.get(user=user_obj)
                                allocationuser_obj.status = AllocationUserStatusChoice.objects.get(name='Removed')
                                allocationuser_obj.usage = 0
                                allocationuser_obj.usage_bytes = 0
                                allocationuser_obj.unit = ''
                                allocationuser_obj.allocation_group_usage_bytes = lab_data["kbytes"]
                                allocationuser_obj.allocation_group_quota = lab_data["quota"]
                                allocationuser_obj.save()
                                allocation.save()
                            except Exception as e:
                                print(f'Error: {e}')
                                # allocation_users.remove(allocation_user) # remove this particular allocation_user

                    for json_user in user_json_dict:
                        try:
                            user_obj = get_user_model().objects.get(username = json_user)
                        except get_user_model().DoesNotExist:
                            print('Cannot find user: ' +json_user)
                            # fullname = user_json_dict[json_user]['name']
                            # fullname_lst = fullname.split()
                            # if (len(fullname_lst) > 1):
                            #     first_name = fullname_lst[0]
                            #     last_name = fullname_lst[1]
                            # else:
                            #     first_name = fullname_lst[0]
                            #     last_name = "" # no last_name
                            # user_obj = get_user_model().objects.create(
                            #     username = json_user,
                            #     first_name = first_name,
                            #     last_name = last_name,
                            #     email = "Not_Active@fas.edu",
                            #     is_active = False,
                            #     is_staff = False,
                            #     is_superuser = False,
                            # )
                            # get_user_model().objects.get(username=json_user).save()

                            # raise Exception(f'Cannot find user {json_user}')

                        try:
                            allocationuser_obj = AllocationUser.objects.get(user=user_obj)
                            print(allocationuser_obj.status)
                            allocationuser_obj.status= AllocationUserStatusChoice.objects.get(name='Active')
                        except AllocationUser.DoesNotExist:
                            # create allocationuser object
                            allocationuser_obj = AllocationUser(
                                allocation=allocation,
                                user=user_obj,
                                status=AllocationUserStatusChoice.objects.get(name='Active'),
                            )

                        # only updating allocation user object
                        usage_string = user_json_dict[json_user]['usage']
                        num, alpha = splitString(usage_string)
                        allocationuser_obj.usage = num
                        allocationuser_obj.usage_bytes = user_json_dict[json_user]['logical_usage']
                        allocationuser_obj.unit = alpha
                        allocationuser_obj.allocation_group_usage_bytes = lab_data["kbytes"]
                        allocationuser_obj.allocation_group_quota = lab_data["quota"]
                        allocationuser_obj.save()
                        allocation.save()
                        # get_user_model().objects.get(username=json_user).save()
            except Exception as e:
                # logger.exception(e)
                print(f'Error: {e}')
