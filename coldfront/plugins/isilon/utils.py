import logging

import isilon_sdk.v9_3_0 as isilon_api
from isilon_sdk.v9_3_0.rest import ApiException

from coldfront.core.utils.common import import_from_settings

logger = logging.getLogger(__name__)

class IsilonConnection:
    """Convenience class containing methods for collecting data from an isilon cluster
    """
    def __init__(self, cluster_name):
        self.cluster_name = cluster_name
        self.api_client = self.connect(cluster_name)
        self.quota_client = isilon_api.QuotaApi(self.api_client)
        self.pools_client = isilon_api.StoragepoolApi(self.api_client)

    def connect(self, cluster_name):
        configuration = isilon_api.Configuration()
        configuration.host = f'http://{cluster_name}01.rc.fas.harvard.edu:8080'
        configuration.username = import_from_settings('ISILON_USER')
        configuration.password = import_from_settings('ISILON_PASS')
        configuration.verify_ssl = False
        api_client = isilon_api.ApiClient(configuration)
        return api_client

    def get_isilon_volume_unallocated_space(self):
        """get the total unallocated space on a volume
        calculated as total usable space minus sum of all quotas on the volume
        """
        try:
            quotas = self.quota_client.list_quota_quotas(type='directory')
            quota_sum = sum(
                [q.thresholds.hard for q in quotas.quotas if q.thresholds.hard])
            pool_query = self.pools_client.get_storagepool_storagepools(
                toplevels=True)
            total_space = pool_query.usage.usable_bytes
            return total_space - quota_sum
        except ApiException as e:
            err = f'ERROR: could not get quota for {self.cluster_name} - {e}'
            print_log_error(e, err)
            return None


def update_isilon_allocation_quota(allocation, quota):
    """Update the quota for an allocation on an isilon cluster

    Parameters
    ----------
    api_instance : isilon_api.QuotaApi
    allocation : coldfront.core.allocation.models.Allocation
    quota : int
    """
    # make isilon connection to the allocation's resource
    isilon_resource = allocation.resources.first().split('/')[0]
    isilon_conn = IsilonConnection(isilon_resource)
    path = f'/ifs/{allocation.path}'

    # check if enough space exists on the volume
    quota_bytes = quota * 1024**3
    unallocated_space = isilon_conn.get_isilon_volume_unallocated_space()
    allowable_space = unallocated_space * 0.8
    if allowable_space < quota_bytes:
        raise ValueError(
            'ERROR: not enough space on volume to set quota to %s for %s'
            % (quota, allocation)
        )
    try:
        isilon_conn.quota_client.update_quota_quota(path=path, threshold_hard=quota)
        print(f"SUCCESS: updated quota for {allocation} to {quota}")
        logger.info("SUCCESS: updated quota for %s to %s", allocation, quota)
    except ApiException as e:
        err = f"ERROR: could not update quota for {allocation} to {quota} - {e}"
        print_log_error(e, err)

def print_log_error(e, message):
    print(f'ERROR: {message} - {e}')
    logger.error("%s - %s", message, e)

def update_coldfront_quota_and_usage(alloc, usage_attribute_type, value_list):
    usage_attribute, _ = alloc.allocationattribute_set.get_or_create(
        allocation_attribute_type=usage_attribute_type
    )
    usage_attribute.value = value_list[0]
    usage_attribute.save()
    usage = usage_attribute.allocationattributeusage
    usage.value = value_list[1]
    usage.save()
    return usage_attribute

