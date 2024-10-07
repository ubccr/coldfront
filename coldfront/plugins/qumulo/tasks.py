from django.db.models import Q
import logging
import os

from coldfront.config.env import ENV
from coldfront.core.allocation.models import (
    Allocation,
    AllocationStatusChoice,
    AllocationAttribute,
    AllocationAttributeType,
    AllocationAttributeUsage,
    AllocationLinkage,
)
from coldfront.core.resource.models import Resource

from coldfront.plugins.qumulo.utils.aces_manager import AcesManager
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

    logger.info("Usages ingested for today: ", daily_usage_ingested)
    logger.info("Usages pulled from QUMULO: ", usage_pulled_from_qumulo)

    success = usage_pulled_from_qumulo == daily_usage_ingested
    if success:
        logger.warn("Successful ingestion of quota daily usage.")
    else:
        logger.warn("Unsuccessful ingestion of quota daily usage. Check the results.")

    return success


class ResetAcl(object):
    qumulo_api = None
    sub_allocations = None

    def __init__(self, allocation: Allocation):
        self.allocation = allocation
        self.debug = ENV.bool('DEBUG', default=False)
        self.fs_path = allocation.get_attribute(name='storage_filesystem_path')
        self.is_allocation_root = QumuloAPI.is_allocation_root_path(
            self.fs_path
        )
        access_allocations = AclAllocations.get_access_allocations(allocation)
        self.rw_group = AclAllocations.get_allocation_rwro_group_name(
            access_allocations,
            'rw'
        )
        self.ro_group = AclAllocations.get_allocation_rwro_group_name(
            access_allocations,
            'ro'
        )
        self.reset_exclude_paths = []
        if self.is_allocation_root:
            self.sub_allocations = []
            links = None
            try:
                links = AllocationLinkage.objects.get(parent=allocation)
            except AllocationLinkage.DoesNotExist:
                pass
            if links is not None:
                for child in links.children.all():
                    self.reset_exclude_paths.append(
                        child \
                            .get_attribute(name='storage_filesystem_path') \
                            .rstrip('/')
                    )
                    self.sub_allocations.append(child)
        else:
            self._setup_qumulo_api()
            self.parent_aces = AclAllocations.get_sub_allocation_parent_aces(
                allocation,
                self.qumulo_api
            )

    # <debugging functions>
    def __log_acl(self, msg):
        global logger
        if not self.debug:
            return None
        logger.warn(msg)

    def __log_acl_reset(self, path):
        self.__log_acl(f'Resetting "directory content" ACLs for path: {path}')
    # </debugging functions>

    # bmulligan 20241004: we use this to make ad-hoc connections to qumulo as
    # the API client gets used throughout this class.  this technique was
    # developed because the framework was complaining that certain sub-classes
    # or dependent objects (SSL-related) "couldn't be pickled"
    def _setup_qumulo_api(self):
        if self.qumulo_api is None:
            self.qumulo_api = QumuloAPI()

    def _set_directory_content_acls(self, contents):
        self._setup_qumulo_api()
        for item in contents:
            item_path = item.get('path', None)
            item_type = item.get('type', None)
            if None in [item_path, item_type]:
                # problem: raise some kind of exception or something
                debug = {'item_path': item_path, 'item_type': item_type}
                continue
            acl = AcesManager.get_base_acl()
            if item_type == 'FS_FILE_TYPE_FILE':
                acl['aces'] = AcesManager.get_allocation_existing_file_aces(
                    self.rw_group,
                    self.ro_group
                )
            elif item_type == 'FS_FILE_TYPE_DIRECTORY':
                acl['aces'] = \
                    AcesManager.get_allocation_existing_directory_aces(
                        self.rw_group,
                        self.ro_group
                    )
                if not self.is_allocation_root:
                    acl['aces'].extend(self.parent_aces)
            self.__log_acl_reset(item_path)
            self.qumulo_api.rc.fs.set_acl_v2(path=item_path, acl=acl)
            if item_type == 'FS_FILE_TYPE_DIRECTORY':
                self._set_directory_content_acls(
                    self._get_directory_contents(item_path, True)
                )

    def _get_directory_contents(self, path, skip_filter=False):
        def filter_helper(item):
            return_value = True
            for path in self.reset_exclude_paths:
                if item['path'].startswith(path):
                    return_value = False
                    break
            return return_value
        self._setup_qumulo_api()
        ed_resp = list(
            self.qumulo_api.rc.fs.enumerate_entire_directory(path=path)
        )
        for entry in ed_resp:
            entry.update(
                (
                    (k, entry['path'].rstrip('/'))
                    for k, v in entry.items() if k == 'path'
                )
            )
        dc = sorted(
            ed_resp,
            key=lambda entry: entry['path']
        )
        if skip_filter:
            return dc
        return list(filter(filter_helper, dc))

    def run_allocation_acl_reset(self):
        self._setup_qumulo_api()
        fs_path = self.fs_path
        acl = AcesManager.get_base_acl()
        # 1.) Clear aces from exisitng ACLs
        if self.is_allocation_root:
            initial_walk_path = f'{fs_path}/Active'
            for path in [fs_path, initial_walk_path]:
                self.qumulo_api.rc.fs.set_acl_v2(path=path, acl=acl)
        else:
            initial_walk_path = fs_path
            self.qumulo_api.rc.fs.set_acl_v2(path=fs_path, acl=acl)
        # 2.) Run logic to set default ACLs on allocation directories
        AclAllocations.reset_allocation_acls(self.allocation, self.qumulo_api)
        # 3.) Walk the directory tree setting default file and directory ACLs
        self.__log_acl(
            f'Starting ACL reset walk with path: {initial_walk_path}'
        )
        self._set_directory_content_acls(
            self._get_directory_contents(initial_walk_path)
        )
        self.__log_acl(
            f'...{initial_walk_path} ACL reset directory walk complete'
        )


def reset_allocation_acls(
    user_email: str,
    allocation: Allocation,
    reset_subs: bool = False
):
    ra_object = ResetAcl(allocation)
    ra_object.run_allocation_acl_reset()
    if reset_subs:
        for sub in ra_object.sub_allocations:
            sub_ra_object = ResetAcl(sub)
            sub_ra_object.run_allocation_acl_reset()
