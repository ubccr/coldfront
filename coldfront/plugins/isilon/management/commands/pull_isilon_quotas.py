import logging

from django.core.management.base import BaseCommand

from coldfront.core.allocation.models import Allocation, AllocationAttributeType
from coldfront.core.resource.models import Resource
from coldfront.plugins.isilon.utils import (
    IsilonConnection,
    print_log_error,
    update_coldfront_quota_and_usage,
)

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """Pull Isilon quotas
    """
    help = 'Pull Isilon quotas'

    def handle(self, *args, **kwargs):
        """For all active tier1 allocations, update quota and usage
        1. run a query that collects all active tier1 allocations
        """
        quota_bytes_attributetype = AllocationAttributeType.objects.get(
            name='Quota_In_Bytes')
        quota_tbs_attributetype = AllocationAttributeType.objects.get(
            name='Storage Quota (TiB)')
        # create isilon connections to all isilon clusters in coldfront
        isilon_resources = Resource.objects.filter(name__contains='tier1')
        for resource in isilon_resources:
            report = {"complete": 0, "no entry": [], "empty quota": []}
            resource_name = resource.name.split('/')[0]
            # try connecting to the cluster. If it fails, display an error and
            # replace the resource with a dummy resource
            try:
                api_instance = IsilonConnection(resource_name)
            except Exception as e:
                message = f'Could not connect to {resource_name} - will not update quotas for allocations on this resource'
                print_log_error(e, message)
                # isilon_clusters[resource.name] = None
                continue

            # get all active allocations for this resource
            isilon_allocations = Allocation.objects.filter(
                status__name='Active',
                resources__name=resource.name,
            )

            # get all allocation quotas and usoges
            try:
                rc_labs = api_instance.quota_client.list_quota_quotas(
                    path='/ifs/rc_labs/', recurse_path_children=True,
                )
                l3_labs = api_instance.quota_client.list_quota_quotas(
                    path='/ifs/rc_fasse_labs/', recurse_path_children=True,
                )
            except Exception as e:
                err = f'Could not connect to {resource_name} - will not update quotas for allocations on this resource'
                print_log_error(e, err)
                # isilon_clusters[resource.name] = None
                continue
            quotas = rc_labs.quotas + l3_labs.quotas
            for allocation in isilon_allocations:
                # get the api_response entry for this allocation. If it doesn't exist, skip
                try:
                    api_entry = next(e for e in quotas if e.path == f'/ifs/{allocation.path}')
                except StopIteration as e:
                    err = f'no isilon quota entry for allocation {allocation}'
                    print_log_error(e, err)
                    report['no entry'].append(f'{allocation.pk} {allocation.path} {allocation}')
                    continue
                # update the quota and usage for this allocation
                quota = api_entry.thresholds.hard
                usage = api_entry.usage.fslogical
                if quota is None:
                    err = f'no hard threshold set for allocation {allocation}'
                    print_log_error(None, err)
                    report['empty quota'].append(f'{allocation.pk} {allocation.path} {allocation}')
                    continue
                quota_tb = quota / 1024 / 1024 / 1024 / 1024
                usage_tb = usage / 1024 / 1024 / 1024 / 1024
                update_coldfront_quota_and_usage(
                    allocation, quota_bytes_attributetype, [quota, usage]
                )
                update_coldfront_quota_and_usage(
                    allocation, quota_tbs_attributetype, [quota_tb, usage_tb]
                )
                print("SUCCESS:update for allocation", allocation, "complete")
                report['complete'] += 1
            print(report)
            logger.warning("isilon update report for %s: %s", resource_name, report)
