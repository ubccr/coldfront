from django.db.models import Q
import logging

from coldfront.core.allocation.models import (
    Allocation,
    AllocationStatusChoice,
    AllocationAttribute,
    AllocationAttributeType,
    AllocationAttributeUsage,
)
from coldfront.core.resource.models import Resource

from coldfront.plugins.qumulo.utils.qumulo_api import QumuloAPI
from coldfront.plugins.qumulo.utils.acl_allocations import AclAllocations
from coldfront.plugins.qumulo.utils.active_directory_api import ActiveDirectoryAPI

from qumulo.lib.request import RequestError

import time
from datetime import datetime

logger = logging.getLogger(__name__)
SECONDS_IN_AN_HOUR = 60 * 60
SECONDS_IN_A_DAY = 24 * SECONDS_IN_AN_HOUR


def poll_ad_group(
    acl_allocation: Allocation,
    expiration_seconds: int = SECONDS_IN_A_DAY,
) -> None:
    qumulo_api = QumuloAPI()

    storage_acl_name = acl_allocation.get_attribute("storage_acl_name")
    group_dn = ActiveDirectoryAPI.generate_group_dn(storage_acl_name)

    success = False

    try:
        qumulo_api.rc.ad.distinguished_name_to_ad_account(group_dn)
        success = True
    except RequestError:
        logger.warn(f'Allocation Group "{group_dn}" not found')
        success = False

    acl_group_name = acl_allocation.get_attribute("storage_acl_name")
    time_since_creation = time.time() - acl_allocation.created.timestamp()

    if success:
        acl_allocation.status = AllocationStatusChoice.objects.get(name="Active")
        logger.warn(f'Allocation Group "{acl_group_name}" found')
    elif time_since_creation > expiration_seconds:
        logger.warn(
            f'Allocation Group "{acl_group_name}" not found after {expiration_seconds/SECONDS_IN_AN_HOUR} hours'
        )
        acl_allocation.status = AllocationStatusChoice.objects.get(name="Expired")

    acl_allocation.save()


def poll_ad_groups() -> None:
    resources = Resource.objects.filter(Q(name="rw") | Q(name="ro"))
    acl_allocations = Allocation.objects.filter(
        status__name="Pending", resources__in=resources
    )

    logger.warn(f"Polling {len(acl_allocations)} ACL allocations")

    for acl_allocation in acl_allocations:
        poll_ad_group(acl_allocation)


def conditionally_update_storage_allocation_status(allocation: Allocation) -> None:
    acl_allocations = AclAllocations.get_access_allocations(allocation)

    for acl_allocation in acl_allocations:
        if acl_allocation.status.name != "Active":
            return

    allocation.status = AllocationStatusChoice.objects.get(name="New")
    allocation.save()


def conditionally_update_storage_allocation_statuses() -> None:
    resource = Resource.objects.get(name="Storage2")
    allocations = Allocation.objects.filter(status__name="Pending", resources=resource)
    logger.warn(f"Checking {len(allocations)} qumulo allocations")

    for allocation in allocations:
        conditionally_update_storage_allocation_status(allocation)


# TODO: refactor the following methods to a service class
def ingest_quotas_with_daily_usage() -> None:
    logger = logging.getLogger("task_qumulo_daily_quota_usages")

    quota_usages = __get_quota_usages_from_qumulo(logger)
    __set_daily_quota_usages(quota_usages, logger)
    __validate_results(quota_usages, logger)


def __get_quota_usages_from_qumulo(logger):
    qumulo_api = QumuloAPI()
    quota_usages = qumulo_api.get_all_quotas_with_usage()
    return quota_usages


def __set_daily_quota_usages(all_quotas, logger) -> None:
    # Iterate and populate allocation_attribute_usage records
    storage_filesystem_path_attribute_type = AllocationAttributeType.objects.get(
        name="storage_filesystem_path"
    )
    for quota in all_quotas["quotas"]:
        path = quota.get("path")

        allocation = __get_allocation_by_attribute(
            storage_filesystem_path_attribute_type, path
        )
        if allocation is None:
            if path[-1] != "/":
                continue

            value = path[:-1]
            logger.warn(f"Attempting to find allocation without the trailing slash...")
            allocation = __get_allocation_by_attribute(
                storage_filesystem_path_attribute_type, value
            )
            if allocation is None:
                continue

        allocation.set_usage("storage_quota", quota.get("capacity_usage"))


def __get_allocation_by_attribute(attribute_type, value):
    try:
        attribute = AllocationAttribute.objects.get(
            value=value, allocation_attribute_type=attribute_type
        )
    except AllocationAttribute.DoesNotExist:
        logger.warn(f"Allocation record for {value} path was not found")
        return None

    logger.warn(f"Allocation record for {value} path was found")
    return attribute.allocation


def __validate_results(quota_usages, logger) -> bool:
    today = datetime.today()
    year = today.year
    month = today.month
    day = today.day

    daily_usage_ingested = AllocationAttributeUsage.objects.filter(
        modified__year=year, modified__month=month, modified__day=day
    ).count()
    usage_pulled_from_qumulo = len(quota_usages["quotas"])

    success = usage_pulled_from_qumulo == daily_usage_ingested
    if success:
        logger.warn("Successful ingestion of quota daily usage.")
    else:
        logger.warn("Unsuccessful ingestion of quota daily usage. Not all the QUMULO usage data was stored in Coldfront.")
        logger.warn(f"Usages pulled from QUMULO: {usage_pulled_from_qumulo}")
        logger.warn(f"Usages ingested for today: {daily_usage_ingested}")

    return success
