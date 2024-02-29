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
        self._total_space = None
        self._allocated_space = None
        self._used_space = None

    def connect(self, cluster_name):
        configuration = isilon_api.Configuration()
        configuration.host = f'http://{cluster_name}01.rc.fas.harvard.edu:8080'
        configuration.username = import_from_settings('ISILON_USER')
        configuration.password = import_from_settings('ISILON_PASS')
        configuration.verify_ssl = False
        api_client = isilon_api.ApiClient(configuration)
        return api_client

    @property
    def total_space(self):
        """total usable disk space"""
        if self._total_space is None:
            pool_query = self.pools_client.get_storagepool_storagepools(
                toplevels=True)
            pools_bytes = [int(sp.usage.usable_bytes) for sp in pool_query.storagepools]
            self._total_space = sum(pools_bytes)
        return self._total_space

    @property
    def allocated_space(self):
        """space claimed by allocations"""
        if self._allocated_space is None:
            quotas = self.quota_client.list_quota_quotas(type='directory')
            self._allocated_space = sum(
                [q.thresholds.hard for q in quotas.quotas if q.thresholds.hard])
        return self._allocated_space

    @property
    def used_space(self):
        """space used by files etc"""
        if self._used_space is None:
            pool_query = self.pools_client.get_storagepool_storagepools(
                toplevels=True)
            pools_bytes = [int(sp.usage.used_bytes) for sp in pool_query.storagepools]
            self._used_space = sum(pools_bytes)
        return self._used_space

    @property
    def unused_space(self):
        """total unused space on a volume"""
        return self.total_space - self.used_space

    @property
    def unallocated_space(self):
        """total unallocated space on a volume"""
        return self.total_space - self.allocated_space

    def to_tb(self, bytes_value):
        return bytes_value / (1024**4)

    def get_quota_from_path(self, path):
        current_quota = self.quota_client.list_quota_quotas(
            path=path, recurse_path_children=False, recurse_path_parents=False, type='directory')
        if len(current_quota.quotas) > 1:
            raise Exception(f'more than one quota returned for quota {self.cluster_name}:{path}')
        if len(current_quota.quotas) == 0:
            raise Exception(f'no quotas returned for quota {self.cluster_name}:{path}')
        return current_quota.quotas[0]


def update_isilon_allocation_quota(allocation, new_quota):
    """Update the quota for an allocation on an isilon cluster

    Parameters
    ----------
    api_instance : isilon_api.QuotaApi
    allocation : coldfront.core.allocation.models.Allocation
    quota : int
    """
    # make isilon connection to the allocation's resource
    isilon_resource = allocation.resources.first().name.split('/')[0]
    isilon_conn = IsilonConnection(isilon_resource)
    path = f'/ifs/{allocation.path}'

    # check if enough space exists on the volume
    new_quota_bytes = new_quota * 1024**4
    unallocated_space = isilon_conn.unallocated_space
    current_quota_obj = isilon_conn.get_quota_from_path(path)
    current_quota = current_quota_obj.thresholds.hard
    logger.warning("changing allocation %s %s from %s (%s TB) to %s (%s TB)",
       allocation.path, allocation, current_quota, allocation.size, new_quota_bytes, new_quota
    )
    if unallocated_space < (new_quota_bytes-current_quota):
        raise ValueError(
            'ERROR: not enough space on volume to set quota to %s TB for %s'
            % (new_quota, allocation)
        )
    if current_quota > new_quota_bytes:
        current_quota_usage = current_quota_obj.usage.physical
        space_needed = new_quota_bytes * .8
        if current_quota_usage > space_needed:
            raise ValueError(
                'ERROR: cannot automatically shrink the size of allocations to a quota smaller than 80 percent of the space in use. Current size: %s Desired size: %s Space used: %s Allocation: %s'
                % (allocation.size, new_quota, allocation.usage, allocation)
            )
    try:
        new_quota_obj = {'thresholds': {'hard': new_quota_bytes}}
        isilon_conn.quota_client.update_quota_quota(new_quota_obj, current_quota_obj.id)
        print(f'SUCCESS: updated quota for {allocation} to {new_quota}')
        logger.info('SUCCESS: updated quota for %s to %s', allocation, new_quota)
    except ApiException as e:
        err = f'ERROR: could not update quota for {allocation} to {new_quota} - {e}'
        print_log_error(e, err)
        raise

def print_log_error(e, message):
    print(f'ERROR: {message} - {e}')
    logger.error('%s - %s', message, e)

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
