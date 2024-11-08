"""
Automatically create CSV of Starfish storage allocations not found in Coldfront.
"""

import logging

import pandas as pd
from django.core.management.base import BaseCommand
from starfish_api_client import RedashAPIClient

from coldfront.core.allocation.models import Allocation
from coldfront.core.utils.common import import_from_settings

logger = logging.getLogger(__name__)

STARFISH_SERVER = import_from_settings('SF_SERVER', 'starfish')
REDASH_KEY = import_from_settings('REDASH_KEY')

class Command(BaseCommand):
    """
    Automatically create CSV of Starfish storage allocations not found in Coldfront.
    """


    def handle(self, *args, **kwargs):
        # query subdirectory data to get allocations from starfish
        redash = RedashAPIClient(STARFISH_SERVER, subdirectory_query_id, REDASH_KEY)
        subdir_results = redash.query()
        data = subdir_results['query_result']['data']['rows']

        # remove entries with no group name or with group names that are not projects
        ignore_groups = ['Domain Users','root', 'bin', 'rc_admin', 'rc_unpriv', None]
        data = [entry for entry in data if entry['group_name'] not in ignore_groups
                    and 'DISABLED' not in entry['group_name']]
        starfish_allocations = [(a['group_name'], a['vol_name'], a['path']) for a in data]
        
        # compare to all existing allocations in coldfront
        allocations = [(a.project.title, a.resources.first().name.split('/')[0], a.path)
                        for a in Allocation.objects.all()]

        # remove vol_name + path matches
        absent_by_path = [a for a in starfish_allocations if not any(a[1]==b[1] and a[2]==b[2] for b in allocations)]
        
        # remove group_name + vol_name matches
        absent_by_path_or_group = [a for a in absent_by_path if not any(a[1]==b[1] and a[0]==b[0] for b in allocations)]
        
        # write rows with no matches to a csv
        df = pd.DataFrame(absent_by_path_or_group, columns=['project_title', 'server', 'path'])
        df.sort_values(by=['project_title','server']).to_csv('local_data/new_allocations.csv', index=False)
