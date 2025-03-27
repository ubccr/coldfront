from django import forms

from coldfront.plugins.qumulo.forms.AllocationForm import AllocationForm


class CreateSubAllocationForm(AllocationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # hide the project field and show the parent allocation instead
        self.fields["project_pk"].widget = forms.HiddenInput()
        self.fields["parent_allocation"] = forms.CharField(
            help_text="The parent of this sub-allocation",
            label="Parent Allocation",
            required=True,
        )

        # display the parent allocation name
        self.fields["parent_allocation"].initial = kwargs["initial"].pop(
            "parent_allocation_name"
        )
        self.fields["parent_allocation"].disabled = True

        # re-order fields so parent allocation field appears at the top
        self.fields = {
            "parent_allocation": self.fields.pop("parent_allocation"),
            **self.fields,
        }
