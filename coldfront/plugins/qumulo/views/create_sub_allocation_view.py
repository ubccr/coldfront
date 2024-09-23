from django.urls import reverse_lazy


from coldfront.core.allocation.models import (
    Allocation,
    AllocationAttribute,
)
from coldfront.plugins.qumulo.forms import CreateSubAllocationForm
from coldfront.plugins.qumulo.views.update_allocation_view import UpdateAllocationView
from coldfront.plugins.qumulo.utils.acl_allocations import AclAllocations
from coldfront.plugins.qumulo.utils.active_directory_api import ActiveDirectoryAPI


class CreateSubAllocationView(UpdateAllocationView):
    form_class = CreateSubAllocationForm
    template_name = "allocation.html"
    success_url = reverse_lazy("home")

    def get_form_kwargs(self):
        kwargs = super(CreateSubAllocationView, self).get_form_kwargs()
        kwargs["user_id"] = self.request.user.id

        allocation_id = self.kwargs.get("allocation_id")
        parent_allocation = Allocation.objects.get(pk=allocation_id)
        parent_allocation_attrs = AllocationAttribute.objects.filter(
            allocation=allocation_id
        )

        form_data = {
            "project_pk": parent_allocation.project.pk,
            "parent_allocation_name": parent_allocation.get_attribute(
                name="storage_name"
            ),
        }

        # jprew - NOTE: storage name and file path should be cleared
        allocation_attribute_keys = [
            "storage_quota",
            "storage_export_path",
            "storage_ticket",
            "cost_center",
            "department_number",
            "technical_contact",
            "billing_contact",
            "service_rate",
        ]
        
        for key in allocation_attribute_keys:
            form_data[key] = self.get_allocation_attribute(
                allocation_attributes=parent_allocation_attrs, attribute_key=key
            )
        
        # for sub-allocations protocols should default to empty
        form_data["protocols"] = []

        access_keys = ["rw", "ro"]
        for key in access_keys:
            form_data[key + "_users"] = self.get_access_users(key, parent_allocation)

        kwargs["initial"] = form_data
        return kwargs

    def form_valid(self, form: CreateSubAllocationForm):
        allocation_id = self.kwargs.get("allocation_id")
        parent_allocation = Allocation.objects.get(pk=allocation_id)
        form.cleaned_data["storage_name"] = self._handle_sub_allocation_scoping(
            form.cleaned_data["storage_name"],
            parent_allocation.get_attribute(name="storage_name"),
        )
        return super().form_valid(form, parent_allocation=parent_allocation)

    def _handle_sub_allocation_scoping(self, sub_allocation_name: str, parent_allocation_name: str):
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

        if sub_allocation_name.startswith(parent_allocation_name) and sub_allocation_name != parent_allocation_name:
            return sub_allocation_name
        return f"{parent_allocation_name}-{sub_allocation_name}"
