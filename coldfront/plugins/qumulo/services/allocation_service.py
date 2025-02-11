from django.shortcuts import get_object_or_404

from django_q.tasks import async_task

from typing import Any, Dict, Optional

import json
import os

from coldfront.core.allocation.models import (
    Allocation,
    AllocationAttribute,
    AllocationAttributeType,
    Project,
    AllocationLinkage,
    AllocationStatusChoice,
    Resource,
    AllocationUserStatusChoice,
    AllocationUser,
)

from coldfront.plugins.qumulo.tasks import addMembersToADGroup
from coldfront.plugins.qumulo.utils.active_directory_api import ActiveDirectoryAPI

from datetime import datetime


class AllocationService:

    # This is the entry point and the only public method for this service
    @staticmethod
    def create_new_allocation(
        form_data: Dict[str, Any], user, parent_allocation: Optional[Allocation] = None
    ):
        if parent_allocation:
            form_data["storage_name"] = (
                AllocationService.__handle_sub_allocation_scoping(
                    form_data["storage_name"],
                    parent_allocation.get_attribute(name="storage_name"),
                )
            )

        project_pk = form_data.get("project_pk")
        project = get_object_or_404(Project, pk=project_pk)

        allocation = Allocation.objects.create(
            project=project,
            justification="",
            quantity=1,
            status=AllocationStatusChoice.objects.get(name="Pending"),
        )

        active_status = AllocationUserStatusChoice.objects.get(name="Active")
        AllocationUser.objects.create(
            allocation=allocation, user=user, status=active_status
        )

        resource = Resource.objects.get(name="Storage2")
        allocation.resources.add(resource)

        AllocationService.__set_allocation_attributes(
            form_data, allocation, parent_allocation
        )

        AllocationService.__set_default_value_allocation_attributes(allocation)

        access_allocations = AllocationService.__create_access_privileges(
            form_data, project, allocation
        )

        active_directory_api = ActiveDirectoryAPI()
        for access_allocation in access_allocations:
            access_users = list(
                AllocationUser.objects.filter(allocation=access_allocation)
            )

            resource = access_allocation.resources.first()
            form_key = f"{resource.name.lower()}_users"
            access_users = form_data[form_key]

            create_group_time = datetime.now()
            active_directory_api.create_ad_group(
                group_name=access_allocation.get_attribute(name="storage_acl_name")
            )
            async_task(
                addMembersToADGroup, access_users, access_allocation, create_group_time
            )

        return {"allocation": allocation, "access_allocations": access_allocations}

    @staticmethod
    def __handle_sub_allocation_scoping(
        sub_allocation_name: str, parent_allocation_name: str
    ):
        """
        NOTE:
          if sub_allocation_name is same as parent, or is completely different, then
          prepend parent name to sub name
          if sub-allocation name provided already *has* parent name prepended (but is not identical to parent name)
          use it directly
        EXAMPLE:
          parent: foo + sub: bar => foo-bar
          parent: foo + sub: foo => foo-foo
          parent: foo + sub: foo-blah => foo-blah
        """
        if (
            sub_allocation_name.startswith(parent_allocation_name)
            and sub_allocation_name != parent_allocation_name
        ):
            return sub_allocation_name
        return f"{parent_allocation_name}-{sub_allocation_name}"

    @staticmethod
    def __create_access_privileges(
        form_data: Dict[str, Any], project: Project, storage_allocation: Allocation
    ) -> list[Allocation]:
        rw_users = {
            "name": "RW Users",
            "resource": "rw",
            "users": form_data["rw_users"],
        }
        ro_users = {
            "name": "RO Users",
            "resource": "ro",
            "users": form_data["ro_users"],
        }

        access_allocations = []

        for value in [rw_users, ro_users]:
            access_allocation = AllocationService.__create_access_allocation(
                value, project, form_data["storage_name"], storage_allocation
            )

            access_allocations.append(access_allocation)

        return access_allocations

    @staticmethod
    def __create_access_allocation(
        access_data: dict,
        project: Project,
        storage_name: str,
        storage_allocation: Allocation,
    ):
        access_allocation = Allocation.objects.create(
            project=project,
            justification=access_data["name"],
            quantity=1,
            status=AllocationStatusChoice.objects.get(name="Pending"),
        )

        storage_acl_name_attribute = AllocationAttributeType.objects.get(
            name="storage_acl_name"
        )
        AllocationAttribute.objects.create(
            allocation_attribute_type=storage_acl_name_attribute,
            allocation=access_allocation,
            value="storage-{0}-{1}".format(storage_name, access_data["resource"]),
        )

        storage_allocation_pk_attribute = AllocationAttributeType.objects.get(
            name="storage_allocation_pk"
        )
        AllocationAttribute.objects.create(
            allocation_attribute_type=storage_allocation_pk_attribute,
            allocation=access_allocation,
            value=storage_allocation.pk,
        )

        resource = Resource.objects.get(name=access_data["resource"])
        access_allocation.resources.add(resource)

        return access_allocation

    @staticmethod
    def __set_allocation_attributes(
        form_data: Dict[str, Any],
        allocation,
        parent_allocation: Optional[Allocation] = None,
    ):
        # NOTE - parent-child linkage handled separately as it is not an
        # attribute like the other fields
        if parent_allocation:
            linkage, _ = AllocationLinkage.objects.get_or_create(
                parent=parent_allocation
            )
            linkage.children.add(allocation)
            linkage.save()

        allocation_attribute_names = [
            "storage_name",
            "storage_ticket",
            "storage_quota",
            "storage_protocols",
            "storage_filesystem_path",
            "storage_export_path",
            "cost_center",
            "department_number",
            "technical_contact",
            "billing_contact",
            "service_rate",
            "billing_cycle",
            "prepaid_time",
            "prepaid_billing_date",
        ]

        # some of the above are optional

        for allocation_attribute_name in allocation_attribute_names:
            allocation_attribute_type = AllocationAttributeType.objects.get(
                name=allocation_attribute_name
            )

            if allocation_attribute_name == "storage_protocols":
                protocols = form_data.get("protocols")

                AllocationAttribute.objects.create(
                    allocation_attribute_type=allocation_attribute_type,
                    allocation=allocation,
                    value=json.dumps(protocols),
                )
            else:
                value = form_data.get(allocation_attribute_name)
                if value is None:
                    continue

                if allocation_attribute_name == "storage_filesystem_path":
                    if parent_allocation is None:
                        storage_root_path = os.environ.get("STORAGE2_PATH", "")
                    else:
                        storage_root_path = "{:s}/Active".format(
                            parent_allocation.get_attribute(
                                name="storage_filesystem_path"
                            )
                        )

                    if not value.startswith(storage_root_path):
                        value = (
                            f'{storage_root_path.rstrip(" /")}/' f'{value.lstrip(" /")}'
                        )

                AllocationAttribute.objects.create(
                    allocation_attribute_type=allocation_attribute_type,
                    allocation=allocation,
                    value=value,
                )

    @staticmethod
    def __set_default_value_allocation_attributes(allocation):
        # handle allocations with built-in defaults differently
        # (since they're not sourced from form_data)

        allocation_defaults = {
            "secure": "No",
            "audit": "No",
            "exempt": "No",
            "subsidized": "No",
        }

        for attr, value in allocation_defaults.items():
            attribute_type = AllocationAttributeType.objects.get(name=attr)
            AllocationAttribute.objects.get_or_create(
                allocation_attribute_type=attribute_type,
                allocation=allocation,
                value=value,
            )
