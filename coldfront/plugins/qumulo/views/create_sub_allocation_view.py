from django.urls import reverse_lazy


from coldfront.core.allocation.models import (
    Allocation,
    AllocationAttribute,
)
from coldfront.plugins.qumulo.forms import CreateSubAllocationForm
from coldfront.plugins.qumulo.views.update_allocation_view import UpdateAllocationView


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
            "billing_exempt",
            "department_number",
            "billing_cycle",
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
        # jprew - skipping update form_valid because *that* skips
        # the base class form_valid

        # TODO - remove this logic from form_valid; it doesn't belong
        # in the view layer
        return super(UpdateAllocationView, self).form_valid(
            form, parent_allocation=parent_allocation
        )
