"""
Automatically create CSV of Starfish storage allocations not found in Coldfront.
"""

import logging

import pandas as pd
from django.core.management.base import BaseCommand

from coldfront.core.allocation.models import Allocation
from coldfront.plugins.sftocf.utils import StarFishRedash


logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    Automatically create CSV of Starfish storage allocations not found in Coldfront.
    """


    def handle(self, *args, **kwargs):
        redash = StarFishRedash()
        subdir_results = redash.submit_query('subdirectory')
        data = subdir_results['query_result']['data']['rows']
        # remove entries with no group name or with group names that are not projects
        data = [entry for entry in data if entry['group_name'] not in
                [None, 'Domain Users','root', 'bin', 'rc_admin', 'rc_unpriv'] 
                    and 'DISABLED' not in entry['group_name']]
        allocations = [(a.project.title, a.resources.first().name.split('/')[0], a.path)
                        for a in Allocation.objects.all()]
        starfish_allocations = [(a['group_name'],a['vol_name'], a['path'])
                        for a in data]
        absent_by_path = [a for a in starfish_allocations if not any(a[1]==b[1] and a[2]==b[2] for b in allocations)]
        absent_by_path_or_group = [a for a in absent_by_path if not any(a[1]==b[1] and a[0]==b[0] for b in allocations)]
        df = pd.DataFrame(absent_by_path_or_group, columns=['project_title','server','path'])
        df.sort_values(by=['project_title','server']).to_csv('local_data/new_allocations.csv', index=False)
