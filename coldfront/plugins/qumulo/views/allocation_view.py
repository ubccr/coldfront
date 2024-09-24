from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.edit import FormView
from django.urls import reverse_lazy, reverse

from typing import Optional

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

from coldfront.plugins.qumulo.forms import AllocationForm
from coldfront.plugins.qumulo.utils.acl_allocations import AclAllocations
from coldfront.plugins.qumulo.validators import validate_filesystem_path_unique

from pathlib import PurePath


class AllocationView(LoginRequiredMixin, FormView):
    form_class = AllocationForm
    template_name = "allocation.html"
    new_allocation = None

    def get_form_kwargs(self):
        kwargs = super(AllocationView, self).get_form_kwargs()
        kwargs["user_id"] = self.request.user.id
        return kwargs

    def form_valid(
        self, form: AllocationForm, parent_allocation: Optional[Allocation] = None
    ):
        form_data = form.cleaned_data
        user = self.request.user

        storage_filesystem_path = form_data.get("storage_filesystem_path")
        is_absolute_path = PurePath(storage_filesystem_path).is_absolute()
        if is_absolute_path:
            absolute_path = storage_filesystem_path
        else:
            # also need to retrieve the parent path if provided
            if parent_allocation:
                # should already contain storage_root path
                root_val = parent_allocation.get_attribute(
                    name="storage_filesystem_path"
                ).strip("/")
                prepend_val = f"{root_val}/Active"
            else:
                storage_root = os.environ.get("STORAGE2_PATH").strip("/")
                prepend_val = storage_root

            absolute_path = f"/{prepend_val}/{storage_filesystem_path}"
        validate_filesystem_path_unique(absolute_path)

        self.new_allocation = AllocationView.create_new_allocation(
            form_data, user, parent_allocation
        )
        self.success_id = self.new_allocation.get("allocation").id

        return super().form_valid(form)

    def get_success_url(self):

        return reverse(
            "qumulo:updateAllocation",
            kwargs={"allocation_id": self.success_id},
        )

    @staticmethod
    def _handle_sub_allocation_scoping(
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
    def create_new_allocation(
        form_data, user, parent_allocation: Optional[Allocation] = None
    ):
        if parent_allocation:
            form_data["storage_name"] = AllocationView._handle_sub_allocation_scoping(
                form_data["storage_name"],
                parent_allocation.get_attribute(name="storage_name"),
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

        AllocationView.set_allocation_attributes(
            form_data, allocation, parent_allocation
        )

        access_allocations = AllocationView.create_access_privileges(
            form_data, project, allocation
        )

        for access_allocation in access_allocations:
            access_users = AllocationUser.objects.filter(allocation=access_allocation)
            AclAllocations.create_ad_group_and_add_users(
                access_users, access_allocation
            )

        return {"allocation": allocation, "access_allocations": access_allocations}

    @staticmethod
    def create_access_privileges(
        form_data: dict, project: Project, storage_allocation: Allocation
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
            access_allocation = AllocationView.create_access_allocation(
                value, project, form_data["storage_name"], storage_allocation
            )

            for username in value["users"]:
                AclAllocations.add_user_to_access_allocation(
                    username, access_allocation
                )

            access_allocations.append(access_allocation)

        return access_allocations

    @staticmethod
    def create_access_allocation(
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
    def set_allocation_attributes(
        form_data: dict, allocation, parent_allocation: Optional[Allocation] = None
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
