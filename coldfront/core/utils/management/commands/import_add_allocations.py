"""
Add allocations specified in local_data/add_allocations.csv
"""
import json
import logging
import datetime

import pandas as pd
from django.conf import settings
from django.core.exceptions import ValidationError, MultipleObjectsReturned
from django.core.management.base import BaseCommand

from coldfront.core.allocation.models import (AllocationUser,
                                            AllocationAttribute,
                                            AllocationAttributeType,
                                            AllocationStatusChoice,
                                            AllocationUserStatusChoice)
from coldfront.core.utils.fasrc import log_missing
from coldfront.core.project.models import Project
from coldfront.core.resource.models import Resource


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
            allo_list_file = './local_data/ready_to_add/add_allocations.csv'
        else:
            allo_list_file = file

        timestamp = datetime.datetime.now()
        added_allocation_csv = f'./local_data/added_allocations_{timestamp}.csv'
        added_allocations_df = pd.DataFrame()
        subdir_type = AllocationAttributeType.objects.get(name="Subdirectory")
        lab_data = pd.read_csv(allo_list_file)
        command_report = {
                'allocations_added': [],
                'allocations_existing': [],
                'missing_projects': [],
                }
        for row in lab_data.itertuples(index=True, name='Pandas'):
            lab_name = row.project_title
            lab_server = row.server
            lab_path = row.path
            resource = Resource.objects.get(name__contains=lab_server).name
            print(lab_name, lab_server)
            try:
                project_obj = Project.objects.get(title=lab_name) # find project
            except Project.DoesNotExist:
                command_report['missing_projects'].append(f'{lab_name}  {lab_server}  {lab_path}')
                continue
            if project_obj == '':
                continue
            try:
                allocation, created = project_obj.allocation_set.get_or_create(
                    resources__name=resource,
                    allocationattribute__value=lab_path,
                    defaults={
                        'status': AllocationStatusChoice.objects.get(name='Active'),
                        'start_date': datetime.datetime.now(),
                        'is_changeable': True,
                        'justification': f'Allocation Information for {lab_name}',
                        }
                    )
            except MultipleObjectsReturned:
                print(f'multiple objects returned for allocation {lab_name}-{lab_server}')
                continue
            # do not modify status of inactive allocations
            if created:
                allocation.resources.add(Resource.objects.get(name=resource))
                AllocationAttribute.objects.create(
                    allocation=allocation,
                    allocation_attribute_type_id=subdir_type.pk,
                    value=lab_path
                    )
                print(f'allocation created: {lab_name}')
                allocation.save()
                command_report['allocations_added'].append(f'{lab_name}  {lab_server}  {lab_path}')
                added_allocations_df = added_allocations_df.append(row, ignore_index=True)
            else:
                command_report['allocations_existing'].append(f'{lab_name}  {lab_server}  {lab_path}')
            if allocation.status.name != 'Active':
                continue
            pi_obj = project_obj.pi
            try:
                _, created = AllocationUser.objects.get_or_create(
                    allocation=allocation,
                    user=pi_obj,
                    defaults={
                    'status': AllocationUserStatusChoice.objects.get(name='Active')}
                )
            except ValidationError:
                logger.debug('adding PI %s to allocation %s failed', pi_obj.username, allocation.pk)
                created = None
            if created:
                print('PI added: ' + pi_obj.username)
        missing_projects = [{'title': title} for title in command_report['missing_projects']]
        if not added_allocations_df.empty:
            added_allocations_df['billing_code'] = None
            added_allocations_df.to_csv(added_allocation_csv, index=False)
        log_missing('project', missing_projects)

        return json.dumps(command_report, indent=2)
