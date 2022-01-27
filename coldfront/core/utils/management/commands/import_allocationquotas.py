import csv
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
                                              AllocationAttributeType)
from coldfront.core.project.models import (Project)
from coldfront.core.resource.models import (Resource, )
from coldfront.config.env import ENV

import pandas as pd

logger = logging.getLogger()

base_dir = settings.BASE_DIR


class Command(BaseCommand):
    help = "./manage.py import_allocationquotas --storagename '' --tier ''"
    def add_arguments(self, parser):
        parser.add_argument(
            '--storagename',
            dest='storage',
            default='holylfs04',
            help='JSON for which server ',
        )
        parser.add_argument(
            '--tier',
            dest='tier',
            default='tier0',
            help='Storage tier',
        )
    
    def handle(self, *args, **options):

        LOCALDATA_ROOT = ENV.str('LOCALDATA_ROOT', default=base_dir)
        storage = options['storage'] 
        print(storage)
        fileName = storage +  "_allocation.csv"
        tier = options['tier']  
        resource_name = storage + '/' + tier
        print("Loading data for: " + resource_name)
        lab_list_file = os.path.join(LOCALDATA_ROOT, 'local_data/',fileName)

         # Missing projects/allocations
        proj_all_header = ['lab', 'resource','type']
        proj_allocation = open('local_data/missing_project_allocation.csv', 'w')
        writer = csv.writer(proj_allocation)
        writer.writerow(proj_all_header)

        lab_data = pd.read_csv(lab_list_file, skiprows=3)

        for row in lab_data.itertuples(index=True, name='Pandas'):
            lab_name = row.lab
            lab_allocation = row.tb_allocation
            lab_usage = row.tb_usage
            print(lab_name, lab_allocation , lab_usage)
            try:
                filtered_query = Project.objects.get(title = lab_name) # find project
                allocations = Allocation.objects.filter(project = filtered_query, resources__name=resource_name, status__name='Active')
                if(allocations.count() == 0):
                    print("Allocation not found:" + lab_name + ": "+resource_name)
                    tocsv = [lab_name,resource_name,"Allocation"]
                    writer.writerow(tocsv) 
                    continue

                allocation= allocations[0]
                if (allocation): # get allocation
                    allocation_attribute_type_obj = AllocationAttributeType.objects.get(
                        name='Storage Quota (TB)')
                    try:
                        allocation_attribute_obj = AllocationAttribute.objects.get(
                            allocation_attribute_type=allocation_attribute_type_obj,
                            allocation=allocation,
                        )
                        allocation_attribute_obj.value = lab_allocation
                        allocation_attribute_obj.save()
                        allocation_attribute_exist = True
                    except AllocationAttribute.DoesNotExist:
                        allocation_attribute_exist = False

                    if (not allocation_attribute_exist):
                        allocation_attribute_obj,_ =AllocationAttribute.objects.get_or_create(
                            allocation_attribute_type=allocation_attribute_type_obj,
                            allocation=allocation,
                            value = lab_allocation)
                        allocation_attribute_type_obj.save()
                    

                    allocation_attribute_obj.allocationattributeusage.value = lab_usage
                    allocation_attribute_obj.allocationattributeusage.save()
                    
                    allocation_attribute_type_payment = AllocationAttributeType.objects.get(
                    name='RequiresPayment')
                    allocation_attribute_obj, _ = AllocationAttribute.objects.get_or_create(
                    allocation_attribute_type=allocation_attribute_type_payment,
                    allocation=lab_allocation,
                    value=True) 
            except Project.DoesNotExist:
                print("Project not found: " + lab_name)
                tocsv = [lab_name,resource_name,"Project"]
                writer.writerow(tocsv) 
                continue
        proj_allocation.close()
     
