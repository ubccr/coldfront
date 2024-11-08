import logging

import pandas as pd
from django.core.management.base import BaseCommand
from starfish_api_client import RedashAPIClient, StarfishAPIClient

from coldfront.core.allocation.models import Allocation, Resource, AllocationAttributeType
from coldfront.core.utils.common import import_from_settings


logger = logging.getLogger(__name__)

COLDFRONT_HOST = import_from_settings('COLDFRONT_HOST')


def make_error_csv(filename, errors):
    csv_path = f"local_data/error_tracking/{filename}.csv"
    error_df = pd.DataFrame(errors)
    error_df['resolved'] = None
    error_df.to_csv(csv_path, index=False)

def create_error(allocation, issue_description, results):
    return {
        "lab": allocation.project.title,
        "allocation": allocation,
        "issue": issue_description,
        "results": results,
        "url": f"https://{COLDFRONT_HOST}/allocation/{allocation.pk}"
    }

def get_allocation_attribute_type_id(name):
    return AllocationAttributeType.objects.get(name=name).id

class Command(BaseCommand):
    """
    collect subdirectory values from starfish redash query and 
    assign them to respective allocations' Subdirectory allocationattribute.

    If a group/user pairing has 0 or >1 allocation, log in an error csv to
    handle manually.
    """

    def handle(self, *args, **kwargs):
        subdir_id = get_allocation_attribute_type_id('Subdirectory')
        errors = []
        
         # query subdirectory data to get allocations from starfish
        redash = RedashAPIClient(STARFISH_SERVER, subdirectory_query_id, REDASH_KEY)
        subdir_results = redash.query()
        data = subdir_results['query_result']['data']['rows']

        # remove entries with no group name
        data = [result for result in data if result['group_name']]

        # get all volume names listed as resources in coldfront
        resource_volume_list = [r.name.split('/')[0] for r in Resource.objects.all()]

        starfishserver = StarfishAPIClient(STARFISH_SERVER, STARFISH_USER, STARFISH_PASSWORD)
        # get all volume names from starfish listed as resources in coldfront
        searched_resources = [v for v in starfishserver.get_volume_names() if v in resource_volume_list]

        # get all allocations of resources both in starfish and coldfront
        allocations = Allocation.objects.filter(resources__in=searched_resources)
        
        for allocation in allocations:
            lab = allocation.project.title.lower()
            resource = allocation.get_parent_resource
            volume = resource.name.split('/')[0].lower()

            matched_subdirs = [entry for entry in data if entry['group_name'].lower() == lab and entry['vol_name'].lower() == volume]

            if not matched_subdirs:
                if allocation.status.name in ['Pending Deactivation', 'Inactive']:
                    # ignore these allocations
                    pass
                else:
                    errors.append(create_error(allocation, "no_results", None))
                continue
            
            if len(matched_subdirs) > 1:
                errors.append(create_error(allocation, "multiple_results", matched_subdirs))
                continue
            
            # should only be one result to get here
            assert len(matched_subdirs) == 1

            allocation.allocationattribute_set.update_or_create(
                allocation_attribute_type_id=subdir_id,
                defaults={'value': matched_subdirs[0]['path']}
            )
        
        # log the errors
        for error in errors:
            logger.error(error)
        
        # write errors to csv
        make_error_csv("subdirs_to_add", errors)

