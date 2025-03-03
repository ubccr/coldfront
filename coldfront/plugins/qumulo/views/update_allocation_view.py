from django.contrib import messages
from django.urls import reverse_lazy
from django_q.tasks import async_task

from typing import Union, Optional
from datetime import datetime

import json
import logging

from coldfront.core.allocation.models import (
    Allocation,
    AllocationAttribute,
    AllocationAttributeType,
    AllocationAttributeChangeRequest,
    AllocationChangeRequest,
    AllocationChangeStatusChoice,
    AllocationLinkage,
    AllocationUser,
)

from coldfront.core.user.models import User

from coldfront.plugins.qumulo.forms import UpdateAllocationForm
from coldfront.plugins.qumulo.hooks import acl_reset_complete_hook
from coldfront.plugins.qumulo.tasks import addMembersToADGroup, reset_allocation_acls
from coldfront.plugins.qumulo.views.allocation_view import AllocationView
from coldfront.plugins.qumulo.utils.acl_allocations import AclAllocations
from coldfront.plugins.qumulo.utils.active_directory_api import ActiveDirectoryAPI


logger = logging.getLogger(__name__)


class UpdateAllocationView(AllocationView):
    form_class = UpdateAllocationForm
    template_name = "update_allocation.html"
    success_url = reverse_lazy("home")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form_title"] = "Update Allocation"
        context["allocation_has_children"] = self._allocation_linkage_exists()
        allocation_id = self.kwargs.get("allocation_id")
        allocation = Allocation.objects.get(pk=allocation_id)
        alloc_status = allocation.status.name

        if alloc_status == "Pending":
            pending_status = True
        else:
            pending_status = False
        context["is_pending"] = pending_status

        return context

    def get_form_kwargs(self):
        kwargs = super(UpdateAllocationView, self).get_form_kwargs()
        kwargs["user_id"] = self.request.user.id

        allocation_id = self.kwargs.get("allocation_id")
        allocation = Allocation.objects.get(pk=allocation_id)
        allocation_attrs = AllocationAttribute.objects.filter(allocation=allocation_id)

        form_data = {
            "project_pk": allocation.project.pk,
        }

        allocation_attribute_keys = [
            "storage_name",
            "storage_quota",
            "protocols",
            "storage_filesystem_path",
            "storage_export_path",
            "storage_ticket",
            "cost_center",
            "billing_exempt",
            "department_number",
            "billing_cycle",
            "technical_contact",
            "billing_contact",
            "service_rate",
            "billing_cycle",
            "prepaid_time",
            "prepaid_billing_date",
            "prepaid_expiration",
        ]
        for key in allocation_attribute_keys:
            form_data[key] = self.get_allocation_attribute(
                allocation_attributes=allocation_attrs, attribute_key=key
            )

        access_keys = ["rw", "ro"]
        for key in access_keys:
            form_data[key + "_users"] = self.get_access_users(key, allocation)

        kwargs["initial"] = form_data
        return kwargs

    def form_valid(
        self, form: UpdateAllocationForm, parent_allocation: Optional[Allocation] = None
    ):
        if "reset_acls" in self.request.POST:
            self._reset_acls()
        else:
            self._updated_fields_handler(form, parent_allocation)
        return super(AllocationView, self).form_valid(form=form)

    def _acl_reset_message(self):
        name = Allocation.objects.get(
            pk=self.kwargs.get("allocation_id")
        ).get_attribute(name="storage_name")
        if self.request.POST.get("reset_sub_acls"):
            message = f"ACL reset initiated for {name} and its sub-allocations."
        else:
            message = f"ACL reset initiated for {name}."
        return message

    def _allocation_linkage_exists(self):
        has_linkage = True
        try:
            AllocationLinkage.objects.get(
                parent=Allocation.objects.get(pk=self.kwargs.get("allocation_id"))
            )
        except AllocationLinkage.DoesNotExist:
            has_linkage = False
        return has_linkage

    def _reset_acls(self):
        # bmulligan (20240903): "retry" and "timeout" are intended to be
        # arbitrarily high values.  It would be good if the application could
        # know or learn what they should be.  Testing has shown that the DEV
        # infrastructure can process a directory tree of about 90,500 items in
        # 62 minutes.
        task_id = async_task(
            reset_allocation_acls,
            User.objects.get(id=self.request.user.id).email,
            Allocation.objects.get(pk=self.kwargs.get("allocation_id")),
            True if self.request.POST.get("reset_sub_acls") == "on" else False,
            hook=acl_reset_complete_hook,
            q_options={"retry": 90000, "timeout": 86400},
        )
        messages.add_message(self.request, messages.SUCCESS, self._acl_reset_message())

    def _updated_fields_handler(
        self, form: UpdateAllocationForm, parent_allocation: Optional[Allocation] = None
    ):
        form_data = form.cleaned_data

        allocation = Allocation.objects.get(pk=self.kwargs.get("allocation_id"))

        allocation_change_request = AllocationChangeRequest.objects.create(
            allocation=allocation,
            status=AllocationChangeStatusChoice.objects.get(name="Pending"),
            justification="updating",
            notes="updating",
            end_date_extension=10,
        )

        # NOTE - "storage_protocols" will have special handling
        attributes_to_check = [
            "cost_center",
            "billing_exempt",
            "department_number",
            "billing_cycle",
            "technical_contact",
            "billing_contact",
            "service_rate",
            "storage_ticket",
            "storage_quota",
        ]

        form_values = [form_data.get(field_name) for field_name in attributes_to_check]

        # handle "storage_protocols" separately
        attributes_to_check.append("storage_protocols")
        form_values.append(json.dumps(form_data.get("protocols")))

        for attribute_name, form_value in zip(attributes_to_check, form_values):
            UpdateAllocationView._handle_attribute_change(
                allocation=allocation,
                allocation_change_request=allocation_change_request,
                attribute_name=attribute_name,
                form_value=form_value,
            )

        # RW and RO users are not handled via an AllocationChangeRequest
        access_keys = ["rw", "ro"]
        for key in access_keys:
            access_users = form_data[key + "_users"]
            self.set_access_users(key, access_users, allocation)

        # needed for redirect logic to work
        self.success_id = str(allocation.id)

    @staticmethod
    def _handle_attribute_change(
        allocation: Allocation,
        allocation_change_request: AllocationChangeRequest,
        attribute_name: str,
        form_value: Union[str, int],
    ) -> None:
        # some attributes are optional and so may not exist
        # if they don't, we want to create them with an empty
        # value so the change request flow will work
        attribute, _ = AllocationAttribute.objects.get_or_create(
            allocation_attribute_type=AllocationAttributeType.objects.get(
                name=attribute_name
            ),
            allocation=allocation,
            defaults={"value": ""},
        )

        # storage quota needs to be compared as an integer
        comparand = int(attribute.value) if type(form_value) is int else attribute.value
        if comparand != form_value:
            AllocationAttributeChangeRequest.objects.create(
                allocation_attribute=attribute,
                allocation_change_request=allocation_change_request,
                new_value=form_value,
            )

    @staticmethod
    def set_access_users(
        access_key: str, access_users: list[str], storage_allocation: Allocation
    ):
        active_directory_api = ActiveDirectoryAPI()

        access_allocation = AclAllocations.get_access_allocation(
            storage_allocation, access_key
        )

        allocation_users = AllocationUser.objects.filter(allocation=access_allocation)
        allocation_usernames = [
            allocation_user.user.username for allocation_user in allocation_users
        ]

        users_to_add = list(set(access_users) - set(allocation_usernames))
        create_group_time = datetime.now()
        async_task(
            addMembersToADGroup, users_to_add, access_allocation, create_group_time
        )

        users_to_remove = set(allocation_usernames) - set(access_users)
        for allocation_username in users_to_remove:
            allocation_users.get(user__username=allocation_username).delete()
            active_directory_api.remove_member_from_group(
                allocation_username,
                access_allocation.get_attribute("storage_acl_name"),
            )

    def get_allocation_attribute(self, allocation_attributes: list, attribute_key: str):
        for allocation_attribute in allocation_attributes:
            if (
                attribute_key == "protocols"
                and allocation_attribute.allocation_attribute_type.name
                == "storage_protocols"
            ):
                return json.loads(allocation_attribute.value)

            if allocation_attribute.allocation_attribute_type.name == attribute_key:
                return allocation_attribute.value

    @staticmethod
    def get_access_users(key: str, storage_allocation: Allocation) -> list[str]:
        access_allocation = AclAllocations.get_access_allocation(
            storage_allocation, key
        )

        access_allocation_users = AllocationUser.objects.filter(
            allocation=access_allocation
        )

        access_users = [
            allocation_user.user.username for allocation_user in access_allocation_users
        ]

        return access_users
