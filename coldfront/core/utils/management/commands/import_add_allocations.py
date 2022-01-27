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
                                              AllocationAttributeType, AllocationStatusChoice, AllocationUser, AllocationUserStatusChoice)
from coldfront.core.project.models import (Project)
from coldfront.core.resource.models import (Resource, )
from coldfront.config.env import ENV

import pandas as pd

logger = logging.getLogger()

base_dir = settings.BASE_DIR


class Command(BaseCommand):

    def handle(self, *args, **options):

        LOCALDATA_ROOT = ENV.str('LOCALDATA_ROOT', default=base_dir)
        allocationFile = "add_allocations.csv"
        allo_list_file = os.path.join(LOCALDATA_ROOT, 'local_data/',allocationFile)

        lab_data = pd.read_csv(allo_list_file)

        for row in lab_data.itertuples(index=True, name='Pandas'):
            lab_name = row.lab
            lab_resource_allocation = row.resource
            print(lab_name, lab_resource_allocation)
            try:
                project_obj = Project.objects.get(title = lab_name) # find project
                allocations = Allocation.objects.filter(project = project_obj, resources__name=lab_resource_allocation, status__name='Active')
                if(allocations.count() == 0):
                    print("creating allocation: " + lab_name)
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
                            Resource.objects.get(name=lab_resource_allocation))
                        allocation_obj.save()
                        allocations = Allocation.objects.filter(project = project_obj,resources__name=lab_resource_allocation, status__name='Active')
                    
                print("Adding PI: " + project_obj.pi.username)
                pi_obj = get_user_model().objects.get(username = project_obj.pi.username)
                allocation_user_obj = AllocationUser.objects.get_or_create(
                allocation=allocations[0],
                user=pi_obj,
                    status=AllocationUserStatusChoice.objects.get(name='Active')
                )
                # allocation_user_obj.save()
                      
            
            except Project.DoesNotExist:
                print("Project not found: " + lab_name)
                continue
     
