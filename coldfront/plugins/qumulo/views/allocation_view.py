from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.edit import FormView
from django.urls import reverse_lazy

from typing import Union

import json
import os

from coldfront.core.allocation.models import (
    Allocation,
    AllocationAttribute,
    AllocationAttributeType,
    Project,
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
    success_url = reverse_lazy("home")

    def get_form_kwargs(self):
        kwargs = super(AllocationView, self).get_form_kwargs()
        kwargs["user_id"] = self.request.user.id
        return kwargs

    def form_valid(
        self, form: AllocationForm, parent_allocation: Union[Allocation, None] = None
    ):
        form_data = form.cleaned_data
        user = self.request.user

        storage_filesystem_path = form_data.get("storage_filesystem_path")
        is_absolute_path = PurePath(storage_filesystem_path).is_absolute()
        if is_absolute_path:
            absolute_path = storage_filesystem_path
        else:
            storage_root = os.environ.get("STORAGE2_PATH").strip("/")
            absolute_path = f"/{storage_root}/{storage_filesystem_path}"
        validate_filesystem_path_unique(absolute_path)

        AllocationView.create_new_allocation(form_data, user, parent_allocation)

        return super().form_valid(form)

    @staticmethod
    def create_new_allocation(
        form_data, user, parent_allocation: Union[Allocation, None] = None
    ):
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
        form_data: dict, allocation, parent_allocation: Union[Allocation, None] = None
    ):
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
                # jprew - for now just skip over them
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
