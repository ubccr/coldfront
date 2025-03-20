"""Utils for interacting with the LFS server."""

from coldfront.core.allocation.models import Allocation
from coldfront.core.resource.models import (
    Resource,
    ResourceAttributeType,
)
from coldfront.plugins.lfs.grpc_client import GrpcClient


# update allocation quotas from quota data
# update tier 0 resource information from lfs volume data
def update_lfs_usages():
    """update lfs resource used_tb and allocated_tb values from filesystem data"""
    client = GrpcClient()
    filesystems = client.list_filesystems()
    allocated_tb_type = ResourceAttributeType.objects.get(name='allocated_tb')
    used_tb_type = ResourceAttributeType.objects.get(name='used_tb')
    free_tb_type = ResourceAttributeType.objects.get(name='free_tb')
    capacity_tb_type = ResourceAttributeType.objects.get(name='capacity_tb')
    for filesystem in filesystems:
        filesystem_name = filesystem.name.replace('/n/', '')
        resource = Resource.objects.filter(name__contains=filesystem_name).first()
        if resource:
            capacity_tb, _ = resource.resourceattribute_set.get_or_create(resource_attribute_type=capacity_tb_type)
            capacity_tb.value = filesystem.size / 1024 / 1024 / 1024 / 1024
            capacity_tb.save()
            allocated_tb, _ = resource.resourceattribute_set.get_or_create(resource_attribute_type=allocated_tb_type)
            allocated_tb.value = filesystem.allocated / 1024 / 1024 / 1024 / 1024
            allocated_tb.save()
            used_tb, _ = resource.resourceattribute_set.get_or_create(resource_attribute_type=used_tb_type)
            used_tb.value = filesystem.used / 1024 / 1024 / 1024 / 1024
            used_tb.save()
            free_tb, _ = resource.resourceattribute_set.get_or_create(resource_attribute_type=free_tb_type)
            free_tb.value = capacity_tb.value - used_tb.value
            free_tb.save()



