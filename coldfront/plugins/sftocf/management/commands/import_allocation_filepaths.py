import logging

import pandas as pd
from django.core.management.base import BaseCommand

from coldfront.core.resource.models import Resource
from coldfront.core.allocation.models import Allocation
from coldfront.plugins.sftocf.utils import StarFishRedash, StarFishServer


logger = logging.getLogger(__name__)

def make_error_csv(filename, errors):
    csv_path = f"local_data/{filename}.csv"
    error_df = pd.DataFrame(errors)
    error_df['resolved'] = None
    error_df.to_csv(csv_path, index=False)

class Command(BaseCommand):
    """
    Identify allocations missing path values and assign them the correct path
    from the starfish redash query.

    If a group/user pairing has 0 or >1 allocation, log in an error csv to
    handle manually.
    """

    def handle(self, *args, **kwargs):
        errors = []
        redash = StarFishRedash()
        subdir_results = redash.submit_query("subdirectory")
        data = subdir_results['query_result']['data']['rows']
        data = [result for result in data if result['group_name']]
        starfishserver = StarFishServer()
        searched_resources = starfishserver.get_volumes_in_coldfront()
        allocations = [
            a for a in
            Allocation.objects.filter(
                resources__name__in=searched_resources, status__name='Active')
            if not a.path
        ]
        for allocation in allocations:
            lab = allocation.project.title
            resource = allocation.get_parent_resource
            volume = resource.name.split('/')[0]
            matched_paths = [
                entry for entry in data
                if entry['group_name'].lower() == lab
                and entry['vol_name'] == volume
            ]
            if not matched_paths:
                errors.append({
                    "lab":lab, "allocation":allocation, "issue": "no_results",
                    "url": f"https://coldfront.rc.fas.harvard.edu/allocation/{allocation.pk}"
                })
                continue
            if len(matched_paths) > 1:
                other_allocations = Allocation.objects.filter(
                    resources__name__contains=volume,
                    project__title=lab
                ).exclude(pk=allocation.pk)
                other_allocations_paths = [a.path for a in other_allocations]
                matched_paths = [
                    entry for entry in matched_paths if entry['path'] not in other_allocations_paths
                ]
                if len(matched_paths) != 1:
                    errors.append({
                        "lab":lab, "allocation":allocation,
                        "issue": "multiple_results", "results": matched_paths,
                        "url": f"https://coldfront.rc.fas.harvard.edu/allocation/{allocation.pk}"
                    })
                    continue
            subdir_value = matched_paths[0]['path']
            allocation.allocationattribute_set.update_or_create(
                allocation_attribute_type_id=8, defaults={'value': subdir_value}
            )
            confirmation = f"added path to allocation {allocation.pk}: {subdir_value}"
            logger.info(confirmation)
            print(confirmation)
        for error in errors:
            logger.error("problem matching path for allocation: %s", error)
            print(error)
        make_error_csv("errors_subdirs_to_add", errors)
