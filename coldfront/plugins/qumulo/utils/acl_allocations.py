from typing import Optional

from coldfront.core.allocation.models import (
    Allocation,
    AllocationAttribute,
    AllocationAttributeType,
    AllocationStatusChoice,
    Resource,
    AllocationUserStatusChoice,
    AllocationUser,
    User,
)

from coldfront.plugins.qumulo.utils.aces_manager import AcesManager
from coldfront.plugins.qumulo.utils.active_directory_api import ActiveDirectoryAPI
from coldfront.plugins.qumulo.utils.qumulo_api import QumuloAPI

from ldap3.core.exceptions import LDAPException

from pathlib import PurePath

import os
from dotenv import load_dotenv

load_dotenv(override=True)


class AclAllocations:
    def __init__(self, project_pk):
        self.project_pk = project_pk

    def add_allocation_users(self, allocation: Allocation, wustlkeys: list):
        for wustlkey in wustlkeys:
            AllocationUser.objects.get_or_create(
                status=AllocationUserStatusChoice.objects.get(name="Active"),
                user=User.objects.get(username=wustlkey),
                allocation=allocation,
            )

    @staticmethod
    def add_user_to_access_allocation(username: str, allocation: Allocation):
        # NOTE - just need to provide the proper username
        # post_save handler will retrieve email, given/surname, etc.
        user_tuple = User.objects.get_or_create(username=username)

        AllocationUser.objects.create(
            allocation=allocation,
            user=user_tuple[0],
            status=AllocationUserStatusChoice.objects.get(name="Active"),
        )

    def create_acl_allocation(
        self, acl_type: str, users: list, active_directory_api=None
    ):
        allocation = Allocation.objects.create(
            project=self.project_pk,
            justification="",
            quantity=1,
            status=AllocationStatusChoice.objects.get(name="Active"),
        )

        resource = Resource.objects.get(name=acl_type)

        allocation.resources.add(resource)

        self.add_allocation_users(allocation=allocation, wustlkeys=users)
        self.set_allocation_attributes(
            allocation=allocation, acl_type=acl_type, wustlkey=users[0]
        )

        try:
            self.create_ad_group_and_add_users(
                wustlkeys=users,
                allocation=allocation,
                active_directory_api=active_directory_api,
            )
        except LDAPException as e:
            Allocation.delete(allocation)

    def create_acl_allocations(self, ro_users: list, rw_users: list):
        active_directory_api = ActiveDirectoryAPI()

        self.create_acl_allocation(
            acl_type="ro", users=ro_users, active_directory_api=active_directory_api
        )
        self.create_acl_allocation(
            acl_type="rw", users=rw_users, active_directory_api=active_directory_api
        )

    @staticmethod
    def create_ad_group_and_add_users(
        wustlkeys: list,
        allocation: Allocation,
        active_directory_api: Optional[ActiveDirectoryAPI] = None,
    ) -> None:
        if not active_directory_api:
            active_directory_api = ActiveDirectoryAPI()

        group_name = allocation.get_attribute(name="storage_acl_name")

        active_directory_api.create_ad_group(group_name)

        for wustlkey in wustlkeys:
            active_directory_api.add_user_to_ad_group(
                wustlkey=wustlkey, group_name=group_name
            )

    @staticmethod
    def get_access_allocation(storage_allocation: Allocation, resource_name: str):
        def filter_func(access_allocation: Allocation):
            try:
                access_allocation.resources.get(name=resource_name)
            except:
                return False

            return True

        access_allocations = AclAllocations.get_access_allocations(storage_allocation)

        access_allocation = next(
            filter(
                filter_func,
                access_allocations,
            ),
            None,
        )

        return access_allocation

    @staticmethod
    def get_access_allocations(qumulo_allocation: Allocation) -> list[Allocation]:
        project_access_allocations = Allocation.objects.filter(
            project=qumulo_allocation.project
        )

        access_allocations = filter(
            lambda access_allocation: access_allocation.get_attribute(
                name="storage_allocation_pk"
            )
            == qumulo_allocation.pk,
            project_access_allocations,
        )

        return list(access_allocations)

    @staticmethod
    def is_base_allocation(path: str):
        STORAGE2_PATH = os.environ.get("STORAGE2_PATH").rstrip("/")

        purePath = PurePath(path)

        return purePath.match(f"{STORAGE2_PATH}/*/")

    @staticmethod
    def remove_acl_access(allocation: Allocation):
        qumulo_api = QumuloAPI()
        acl_allocations = AclAllocations.get_access_allocations(allocation)
        fs_path = allocation.get_attribute(name="storage_filesystem_path")

        for acl_allocation in acl_allocations:
            acl = qumulo_api.rc.fs.get_acl_v2(fs_path)

            group_name = acl_allocation.get_attribute(name="storage_acl_name")

            filtered_aces = filter(
                lambda ace: ace["trustee"]["name"] != group_name, acl["aces"]
            )

            acl["aces"] = list(filtered_aces)

            qumulo_api.rc.fs.set_acl_v2(acl=acl, path=fs_path)

            acl_allocation.status = AllocationStatusChoice.objects.get(name="Revoked")
            acl_allocation.save()

    def set_allocation_attributes(
        self, allocation: Allocation, acl_type: str, wustlkey: str
    ):
        allocation_attribute_type = AllocationAttributeType.objects.get(
            name="storage_acl_name"
        )

        AllocationAttribute.objects.create(
            allocation_attribute_type=allocation_attribute_type,
            allocation=allocation,
            value=f"storage-{wustlkey}-{acl_type}",
        )

    @staticmethod
    def set_allocation_acls(
        base_allocation: Allocation,
        qumulo_api: QumuloAPI,
    ):
        fs_path = base_allocation.get_attribute("storage_filesystem_path")
        acl = qumulo_api.rc.fs.get_acl_v2(fs_path)

        access_allocations = AclAllocations.get_access_allocations(base_allocation)
        rw_allocation = next(
            filter(
                lambda access_allocation: access_allocation.resources.filter(
                    name="rw"
                ).exists(),
                access_allocations,
            )
        )
        ro_allocation = next(
            filter(
                lambda access_allocation: access_allocation.resources.filter(
                    name="ro"
                ).exists(),
                access_allocations,
            )
        )

        rw_groupname = rw_allocation.get_attribute(name="storage_acl_name")
        ro_groupname = ro_allocation.get_attribute(name="storage_acl_name")

        acl["aces"].extend(AcesManager.get_allocation_aces(rw_groupname, ro_groupname))

        is_base_allocation = QumuloAPI.is_allocation_root_path(fs_path)

        AclAllocations.set_traverse_acl(
            fs_path=fs_path,
            rw_groupname=rw_groupname,
            ro_groupname=ro_groupname,
            qumulo_api=qumulo_api,
            is_base_allocation=is_base_allocation,
        )

        if is_base_allocation:
            fs_path = f"{fs_path}/Active"
        qumulo_api.rc.fs.set_acl_v2(acl=acl, path=fs_path)

    @staticmethod
    def set_traverse_acl(
        fs_path: str,
        rw_groupname: str,
        ro_groupname: str,
        is_base_allocation,
        qumulo_api: QumuloAPI,
    ):
        if is_base_allocation:
            fs_path = f"{fs_path}/Active"

        path_parents = list(map(lambda parent: str(parent), PurePath(fs_path).parents))
        storage_env_path = (
            f'{os.environ.get("STORAGE2_PATH", "").rstrip().rstrip("/")}' "/"
        )

        for path in path_parents:
            if path.startswith(f"{storage_env_path}"):
                traverse_acl = qumulo_api.rc.fs.get_acl_v2(path)
                # bmulligan (20240730): might want to filter duplicates here
                traverse_acl["aces"].extend(
                    AcesManager.get_traverse_aces(
                        rw_groupname, ro_groupname, is_base_allocation
                    )
                )

                qumulo_api.rc.fs.set_acl_v2(acl=traverse_acl, path=path)
