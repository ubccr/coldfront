from coldfront.core.allocation.models import (
    Allocation,
    AllocationAttribute,
    AllocationAttributeType,
    AllocationLinkage,
    AllocationStatusChoice,
    AllocationUserStatusChoice,
    AllocationUser,
    User,
)
from coldfront.core.user.models import UserProfile

from coldfront.plugins.qumulo.utils.aces_manager import AcesManager
from coldfront.plugins.qumulo.utils.qumulo_api import QumuloAPI

from ldap3.core.exceptions import LDAPException

from pathlib import PurePath

import copy
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
    def add_user_to_access_allocation(
        username: str, allocation: Allocation, is_group: bool = False
    ):
        # NOTE - just need to provide the proper username
        # post_save handler will retrieve email, given/surname, etc.
        user_tuple = User.objects.get_or_create(username=username)

        user_profile = UserProfile.objects.get(user=user_tuple[0])
        user_profile.is_group = is_group
        user_profile.save()

        AllocationUser.objects.create(
            allocation=allocation,
            user=user_tuple[0],
            status=AllocationUserStatusChoice.objects.get(name="Active"),
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
    def get_allocation_rwro_group_name(access_allocations, rwro):
        allocation = next(
            filter(
                lambda access_allocation: access_allocation.resources.filter(
                    name=rwro
                ).exists(),
                access_allocations,
            )
        )
        return allocation.get_attribute(name="storage_acl_name")

    @staticmethod
    def reset_allocation_acls(allocation: Allocation, qumulo_api: QumuloAPI):
        allocation_linkage = AllocationLinkage.objects.filter(parent=allocation)
        # data not sane if len is not 1 or 0
        if len(allocation_linkage) == 1:
            for sub_allocation in allocation_linkage[0].children.all():
                fs_path = sub_allocation.get_attribute("storage_filesystem_path")
                access_allocations = AclAllocations.get_access_allocations(
                    sub_allocation
                )
                rw_groupname = AclAllocations.get_allocation_rwro_group_name(
                    access_allocations, "rw"
                )
                ro_groupname = AclAllocations.get_allocation_rwro_group_name(
                    access_allocations, "ro"
                )
                AclAllocations.set_traverse_acl(
                    fs_path=fs_path,
                    rw_groupname=rw_groupname,
                    ro_groupname=ro_groupname,
                    qumulo_api=qumulo_api,
                    is_base_allocation=False,
                )
        return AclAllocations.set_or_reset_allocation_acls(allocation, qumulo_api, True)

    @staticmethod
    def set_allocation_acls(
        allocation: Allocation,
        qumulo_api: QumuloAPI,
    ):
        return AclAllocations.set_or_reset_allocation_acls(
            allocation, qumulo_api, False
        )

    @staticmethod
    def set_or_reset_allocation_acls(
        allocation: Allocation, qumulo_api: QumuloAPI, reset: bool
    ):
        fs_path = allocation.get_attribute("storage_filesystem_path")
        is_base_allocation = QumuloAPI.is_allocation_root_path(fs_path)

        access_allocations = AclAllocations.get_access_allocations(allocation)
        rw_groupname = AclAllocations.get_allocation_rwro_group_name(
            access_allocations, "rw"
        )
        ro_groupname = AclAllocations.get_allocation_rwro_group_name(
            access_allocations, "ro"
        )

        AclAllocations.set_traverse_acl(
            fs_path=fs_path,
            rw_groupname=rw_groupname,
            ro_groupname=ro_groupname,
            qumulo_api=qumulo_api,
            is_base_allocation=is_base_allocation,
        )

        acl = qumulo_api.rc.fs.get_acl_v2(fs_path)
        aces = copy.deepcopy(acl["aces"])

        if is_base_allocation:
            aces.extend(AcesManager.default_copy())
            acl["aces"] = AcesManager.filter_duplicates(aces)
            qumulo_api.rc.fs.set_acl_v2(acl=acl, path=fs_path)
            aces.extend(AcesManager.get_allocation_aces(rw_groupname, ro_groupname))
            acl["aces"] = AcesManager.filter_duplicates(aces)
            qumulo_api.rc.fs.set_acl_v2(acl=acl, path=f"{fs_path}/Active")
        else:
            for extension in [
                AcesManager.default_copy(),
                AcesManager.get_allocation_aces(rw_groupname, ro_groupname),
            ]:
                aces.extend(extension)
            if reset:
                aces.extend(
                    AclAllocations.get_sub_allocation_parent_directory_aces(
                        allocation, qumulo_api
                    )
                )
            acl["aces"] = AcesManager.filter_duplicates(aces)
            qumulo_api.rc.fs.set_acl_v2(acl=acl, path=fs_path)

    # 20240910: It has been updated to return "standard" access aces for parent
    # ACL groups on a sub-allocation so those aces can be added to those for
    # the sub-allocation ACL groups.
    @staticmethod
    def get_sub_allocation_parent_directory_aces(
        allocation: Allocation, qumulo_api: QumuloAPI
    ):
        # 1.) use linkage to get parent and parent groups
        parent = AllocationLinkage.objects.get(children=allocation).parent
        access_allocations = AclAllocations.get_access_allocations(parent)
        rw_group = AclAllocations.get_allocation_rwro_group_name(
            access_allocations, "rw"
        )
        ro_group = AclAllocations.get_allocation_rwro_group_name(
            access_allocations, "ro"
        )

        # 2.) return ACL "aces" for parent groups
        return AcesManager.get_allocation_aces(rw_group, ro_group)

    @staticmethod
    def get_sub_allocation_parent_file_aces(
        allocation: Allocation, qumulo_api: QumuloAPI
    ):
        parent = AllocationLinkage.objects.get(children=allocation).parent
        access_allocations = AclAllocations.get_access_allocations(parent)
        rw_group = AclAllocations.get_allocation_rwro_group_name(
            access_allocations, "rw"
        )
        ro_group = AclAllocations.get_allocation_rwro_group_name(
            access_allocations, "ro"
        )
        # get the aces needed from the parent allocation for files in the child
        # allocation
        return AcesManager.get_allocation_file_aces(rw_group, ro_group)

    @staticmethod
    def set_traverse_acl(
        fs_path: str,
        rw_groupname: str,
        ro_groupname: str,
        is_base_allocation: bool,
        qumulo_api: QumuloAPI,
    ):
        if is_base_allocation:
            fs_path = f"{fs_path}/Active"

        path_parents = list(map(lambda parent: str(parent), PurePath(fs_path).parents))
        storage_env_path = f'{os.environ.get("STORAGE2_PATH", "").rstrip(" /")}/'

        for path in path_parents:
            if path.startswith(f"{storage_env_path}"):
                traverse_acl = qumulo_api.rc.fs.get_acl_v2(path)
                aces = copy.deepcopy(traverse_acl["aces"])
                aces.extend(
                    AcesManager.get_traverse_aces(
                        rw_groupname, ro_groupname, is_base_allocation
                    )
                )

                traverse_acl["aces"] = AcesManager.filter_duplicates(aces)
                qumulo_api.rc.fs.set_acl_v2(acl=traverse_acl, path=path)
