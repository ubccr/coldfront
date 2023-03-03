'''
Add allocations specified in local_data/add_allocations.csv
'''
import datetime
import os
import logging

import pandas as pd
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, MultipleObjectsReturned
from django.core.management.base import BaseCommand

from coldfront.core.allocation.models import (Allocation,
                                            AllocationUser,
                                            AllocationStatusChoice,
                                            AllocationUserStatusChoice)
from coldfront.core.project.models import Project
from coldfront.core.resource.models import Resource
from coldfront.config.env import ENV


logger = logging.getLogger()

base_dir = settings.BASE_DIR


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            dest='file',
            default=None,
            help='allocation file',
        )

    def handle(self, *args, **options):
        file = file = options['file']
        if not file:
            LOCALDATA_ROOT = ENV.str('LOCALDATA_ROOT', default=base_dir)
            allocation_file = 'add_allocations.csv'
            allo_list_file = os.path.join(LOCALDATA_ROOT, 'local_data/', allocation_file)
        else:
            allo_list_file = file

        lab_data = pd.read_csv(allo_list_file)
        command_report = {
                'allocations_added': [],
                'allocations_existing': [],
                'missing_projects': [],
                }
        for row in lab_data.itertuples(index=True, name='Pandas'):
            lab_name = row.lab
            lab_resource_allocation = row.resource
            lab_path = row.path
            print(lab_name, lab_resource_allocation)
            try:
                project_obj = Project.objects.get(title=lab_name) # find project
            except Project.DoesNotExist:
                command_report['missing_projects'].append(lab_name)
                continue
            if project_obj == '':
                continue
            try:
                allocation, created = project_obj.allocation_set.get_or_create(
                    resources__name=lab_resource_allocation,
                    path=lab_path,
                    defaults={
                        'status': AllocationStatusChoice.objects.get(name='Active'),
                        'start_date': datetime.datetime.now(),
                        'justification': f'Allocation Information for {lab_name}',
                        }
                    )
            except MultipleObjectsReturned:
                print(f'multiple objects returned for allocation {lab_name}-{lab_resource_allocation}')
            # do not modify status of inactive allocations
            if created:
                print(f'allocation created: {lab_name}')
                allocation.resources.add(
                Resource.objects.get(name=lab_resource_allocation))
                allocation.save()
                command_report['allocations_added'].append(allocation)
            else:
                command_report['allocations_existing'].append(allocation)
            if allocation.status.name != 'Active':
                continue
            print('Adding PI: ' + project_obj.pi.username)
            pi_obj = project_obj.pi
            try:
                AllocationUser.objects.get_or_create(
                    allocation=allocation,
                    user=pi_obj,
                    defaults={
                    'status': AllocationUserStatusChoice.objects.get(name='Active')}
                )
            except ValidationError:
                logger.debug('adding PI %s to allocation %s failed', pi_obj.pi.username, allocation.pk)
        return command_report
