from django.db.models import Q
from django.contrib.auth.models import User
from django_q.tasks import async_task

import json
import logging

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
from coldfront.core.utils.mail import send_email_template, email_template_context
from coldfront.core.utils.common import import_from_settings

from coldfront.plugins.qumulo.utils.aces_manager import AcesManager
from coldfront.plugins.qumulo.utils.qumulo_api import QumuloAPI
from coldfront.plugins.qumulo.utils.acl_allocations import AclAllocations
from coldfront.plugins.qumulo.utils.active_directory_api import ActiveDirectoryAPI

from qumulo.lib.request import RequestError

import time
from datetime import datetime

from typing import Optional

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

    qumulo_api = QumuloAPI()
    quota_usages = qumulo_api.get_all_quotas_with_usage()["quotas"]
    base_allocation_quota_usages = list(
        filter(
            lambda quota_usage: AclAllocations.is_base_allocation(quota_usage["path"]),
            quota_usages,
        )
    )

    __set_daily_quota_usages(base_allocation_quota_usages, logger)
    __validate_results(base_allocation_quota_usages, logger)


def addMembersToADGroup(
    wustlkeys: list[str],
    acl_allocation: Allocation,
    bad_keys: Optional[list[str]] = None,
    good_keys: Optional[list[dict]] = None,
) -> None:
    if bad_keys is None:
        bad_keys = []
    if good_keys is None:
        good_keys = []

    if len(wustlkeys) == 0:
        return __ad_members_and_handle_errors(
            wustlkeys, acl_allocation, good_keys, bad_keys
        )

    active_directory_api = ActiveDirectoryAPI()
    wustlkey = wustlkeys[0]

    try:
        member = active_directory_api.get_member(wustlkey)
        is_group = "group" in member["attributes"]["objectClass"]

        good_keys.append(
            {"wustlkey": wustlkey, "dn": member["dn"], "is_group": is_group}
        )
    except ValueError:
        bad_keys.append(wustlkey)

    async_task(addMembersToADGroup, wustlkeys[1:], acl_allocation, bad_keys, good_keys)


def __ad_members_and_handle_errors(
    wustlkeys: list[str],
    acl_allocation: Allocation,
    good_keys: list[dict],
    bad_keys: list[str],
) -> None:
    active_directory_api = ActiveDirectoryAPI()
    group_name = acl_allocation.get_attribute("storage_acl_name")

    if len(good_keys) > 0:
        member_dns = [member["dn"] for member in good_keys]
        try:
            active_directory_api.add_members_to_ad_group(member_dns, group_name)
        except Exception as e:
            logger.error(f"Error adding users to AD group: {e}")
            __send_error_adding_users_email(acl_allocation, wustlkeys)
            return

        for member in good_keys:
            AclAllocations.add_user_to_access_allocation(
                member["wustlkey"], acl_allocation, member["is_group"]
            )
    if len(bad_keys) > 0:
        __send_invalid_users_email(acl_allocation, bad_keys)
    return


def __send_error_adding_users_email(
    acl_allocation: Allocation, wustlkeys: list[str]
) -> None:
    ctx = email_template_context()

    CENTER_BASE_URL = import_from_settings("CENTER_BASE_URL")
    ctx["allocation_url"] = f"{CENTER_BASE_URL}/allocation/{acl_allocation.id}"
    ctx["access_type"] = (
        "Read Only" if acl_allocation.resources.first().name == "ro" else "Read Write"
    )
    ctx["wustlkeys"] = wustlkeys

    user_support_users = User.objects.filter(groups__name="RIS_UserSupport")
    user_support_emails = [user.email for user in user_support_users if user.email]

    send_email_template(
        subject="Error adding users to Storage Allocation",
        template_name="email/error_adding_users.txt",
        template_context=ctx,
        sender=import_from_settings("DEFAULT_FROM_EMAIL"),
        receiver_list=user_support_emails,
    )


def __send_invalid_users_email(acl_allocation: Allocation, bad_keys: list[str]) -> None:
    ctx = email_template_context()

    CENTER_BASE_URL = import_from_settings("CENTER_BASE_URL")
    ctx["allocation_url"] = f"{CENTER_BASE_URL}/allocation/{acl_allocation.id}"
    ctx["access_type"] = (
        "Read Only" if acl_allocation.resources.first().name == "ro" else "Read Write"
    )
    ctx["invalid_users"] = bad_keys

    user_support_users = User.objects.filter(groups__name="RIS_UserSupport")
    user_support_emails = [user.email for user in user_support_users if user.email]

    send_email_template(
        subject="Users not found in Storage Allocation",
        template_name="email/invalid_users.txt",
        template_context=ctx,
        sender=import_from_settings("DEFAULT_FROM_EMAIL"),
        receiver_list=user_support_emails,
    )


def __set_daily_quota_usages(quotas, logger) -> None:
    # Iterate and populate allocation_attribute_usage records
    storage_filesystem_path_attribute_type = AllocationAttributeType.objects.get(
        name="storage_filesystem_path"
    )
    active_status = AllocationStatusChoice.objects.get(name="Active")

    for quota in quotas:
        path = quota.get("path")

        allocation = __get_allocation_by_attribute(
            storage_filesystem_path_attribute_type, path, active_status
        )
        if allocation is None:
            if path[-1] != "/":
                continue

            value = path[:-1]
            logger.warn(f"Attempting to find allocation without the trailing slash...")
            allocation = __get_allocation_by_attribute(
                storage_filesystem_path_attribute_type, value, active_status
            )
            if allocation is None:
                continue

        allocation.set_usage("storage_quota", quota.get("capacity_usage"))


def __get_allocation_by_attribute(attribute_type, value, for_status):
    try:
        attribute = AllocationAttribute.objects.select_related("allocation").get(
            value=value,
            allocation_attribute_type=attribute_type,
            allocation__status=for_status,
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
    usage_pulled_from_qumulo = len(quota_usages)

    success = usage_pulled_from_qumulo == daily_usage_ingested
    if success:
        logger.warn("Successful ingestion of quota daily usage.")
    else:
        logger.warn(
            "Unsuccessful ingestion of quota daily usage. Not all the QUMULO usage data was stored in Coldfront."
        )
        logger.warn(f"Usages pulled from QUMULO: {usage_pulled_from_qumulo}")
        logger.warn(f"Usages ingested for today: {daily_usage_ingested}")

    return success


class ResetAcl:
    qumulo_api = None
    sub_allocations = None

    def __init__(self, allocation: Allocation):
        self.allocation = allocation
        self.debug = ENV.bool("DEBUG", default=False)
        self.fs_path = allocation.get_attribute(name="storage_filesystem_path")
        self.is_allocation_root = QumuloAPI.is_allocation_root_path(self.fs_path)
        access_allocations = AclAllocations.get_access_allocations(allocation)
        self.rw_group = AclAllocations.get_allocation_rwro_group_name(
            access_allocations, "rw"
        )
        self.ro_group = AclAllocations.get_allocation_rwro_group_name(
            access_allocations, "ro"
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
                        child.get_attribute(name="storage_filesystem_path").rstrip("/")
                    )
                    self.sub_allocations.append(child)
        else:
            self._setup_qumulo_api()
            self.parent_directory_aces = (
                AclAllocations.get_sub_allocation_parent_directory_aces(
                    allocation, self.qumulo_api
                )
            )
            self.parent_file_aces = AclAllocations.get_sub_allocation_parent_file_aces(
                allocation, self.qumulo_api
            )

    def __log_acl(self, msg):
        global logger
        if not self.debug:
            return None
        logger.warn(msg)

    def __log_acl_reset(self, path):
        self.__log_acl(f'Resetting "directory content" ACLs for path: {path}')

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
            item_path = item.get("path", None)
            item_type = item.get("type", None)

            if None in [item_path, item_type]:
                msg_data = {"path": item_path, "type": item_type}
                raise BadDirectoryEntry(
                    f"Improper null value found in: {json.dumps(msg_data)}"
                )

            acl = AcesManager.get_base_acl()
            if item_type == "FS_FILE_TYPE_FILE":
                acl["aces"] = AcesManager.get_allocation_existing_file_aces(
                    self.rw_group, self.ro_group
                )
                if not self.is_allocation_root:
                    acl["aces"].extend(self.parent_file_aces)
            elif item_type == "FS_FILE_TYPE_DIRECTORY":
                acl["aces"] = AcesManager.get_allocation_existing_directory_aces(
                    self.rw_group, self.ro_group
                )
                if not self.is_allocation_root:
                    acl["aces"].extend(self.parent_directory_aces)

            self.qumulo_api.rc.fs.set_acl_v2(path=item_path, acl=acl)

            if item_type == "FS_FILE_TYPE_DIRECTORY":
                self._set_directory_content_acls(
                    self._get_directory_contents(item_path, True)
                )

    def _get_directory_contents(self, path, skip_filter=False):
        def filter_helper(item):
            return_value = True
            for path in self.reset_exclude_paths:
                if item["path"].startswith(path):
                    return_value = False
                    break
            return return_value

        self._setup_qumulo_api()
        enumerated_directory = list(
            self.qumulo_api.rc.fs.enumerate_entire_directory(path=path)
        )
        for entry in enumerated_directory:
            entry.update(
                (
                    (k, entry["path"].rstrip("/"))
                    for k, v in entry.items()
                    if k == "path"
                )
            )
        directory_contents = sorted(
            enumerated_directory, key=lambda entry: entry["path"]
        )
        if skip_filter:
            return directory_contents
        return list(filter(filter_helper, directory_contents))

    def run_allocation_acl_reset(self):
        self._setup_qumulo_api()
        fs_path = self.fs_path
        acl = AcesManager.get_base_acl()

        # 1.) Clear aces from exisitng ACLs
        if self.is_allocation_root:
            initial_walk_path = f"{fs_path}/Active"
            for path in [fs_path, initial_walk_path]:
                self.qumulo_api.rc.fs.set_acl_v2(path=path, acl=acl)
        else:
            initial_walk_path = fs_path
            self.qumulo_api.rc.fs.set_acl_v2(path=fs_path, acl=acl)

        # 2.) Run logic to set default ACLs on allocation directories
        AclAllocations.reset_allocation_acls(self.allocation, self.qumulo_api)

        # 3.) Walk the directory tree setting default file and directory ACLs
        self.__log_acl(f"Starting ACL reset walk with path: {initial_walk_path}")
        self._set_directory_content_acls(
            self._get_directory_contents(initial_walk_path)
        )
        self.__log_acl(f"...{initial_walk_path} ACL reset directory walk complete")


def reset_allocation_acls(
    user_email: str, allocation: Allocation, reset_subs: bool = False
):
    ra_object = ResetAcl(allocation)
    ra_object.run_allocation_acl_reset()
    if reset_subs:
        for sub in ra_object.sub_allocations:
            sub_ra_object = ResetAcl(sub)
            sub_ra_object.run_allocation_acl_reset()


class BadDirectoryEntry(Exception):
    pass
