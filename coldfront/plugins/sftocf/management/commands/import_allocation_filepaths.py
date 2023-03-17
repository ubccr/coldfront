import logging

import pandas as pd
from django.core.management.base import BaseCommand

from coldfront.core.resource.models import Resource
from coldfront.core.allocation.models import Allocation
from coldfront.plugins.sftocf.utils import StarFishRedash, compare_cf_sf_volumes, STARFISH_SERVER


logger = logging.getLogger(__name__)

def make_error_csv(filename, errors):
    csv_path = f"local_data/error_tracking/{filename}.csv"
    error_df = pd.DataFrame(errors)
    error_df['resolved'] = None
    error_df.to_csv(csv_path, index=False)

class Command(BaseCommand):
    '''
    collect LFS and Isilon subdir values from starfish redash query; assign them
    to respective allocations' Subdirectory allocationattribute.

    If a group/user pairing has 0 or >1 allocation, log in an error csv to
    handle manually.
    '''

    def handle(self, *args, **kwargs):
        errors = []
        redash = StarFishRedash(STARFISH_SERVER)
        subdir_results = redash.submit_query("subdirectory")
        data = subdir_results['query_result']['data']['rows']
        data = [result for result in data if result['group_name']]
        vols_to_collect = compare_cf_sf_volumes()
        searched_resources = [Resource.objects.get(name__contains=vol) for vol in vols_to_collect]
        allocations = Allocation.objects.filter(resources__in=searched_resources)
        for allocation in allocations:
            lab = allocation.project.title
            resource = allocation.get_parent_resource
            volume = resource.name.split('/')[0]
            matched_subdirs = [entry for entry in data if entry['group_name'].lower() == lab
            and entry['vol_name'] == volume]
            if not matched_subdirs:
                if allocation.status.name == "Inactive":
                    pass
                    # errors.append({"lab":lab, "allocation":allocation, "issue": "no_results_inactive","url": f"https://coldfront.rc.fas.harvard.edu/allocation/{allocation.pk}"})
                else:
                    errors.append({"lab":lab, "allocation":allocation, "issue": "no_results",
                        "url": f"https://coldfront.rc.fas.harvard.edu/allocation/{allocation.pk}"})
                # logger.warning('WARNING: No starfish result for %s %s', lab, resource)
                continue
            if len(matched_subdirs) > 1:
                errors.append({ "lab":lab, "allocation":allocation,
                                "issue": "multiple_results", "results": matched_subdirs,
                                "url": f"https://coldfront.rc.fas.harvard.edu/allocation/{allocation.pk}"})
                continue
            subdir_value = matched_subdirs[0]['path']
            allocation.allocationattribute_set.update_or_create(
                                    allocation_attribute_type_id=8,
                                    defaults={'value': subdir_value})
        make_error_csv("subdirs_to_add", errors)
