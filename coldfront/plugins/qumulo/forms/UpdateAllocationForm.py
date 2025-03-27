from coldfront.plugins.qumulo.forms.AllocationForm import AllocationForm
from django import forms


class UpdateAllocationForm(AllocationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["storage_name"].disabled = True
        self.fields["storage_filesystem_path"].disabled = True

        self.fields["storage_filesystem_path"].validators = []
        self.fields["storage_name"].validators = []

        self.fields["prepaid_expiration"] = forms.DateTimeField(
            help_text="Allocation is paid until this date",
            label="Prepaid Expiration Date",
            required=False,
        )
        self.fields["prepaid_expiration"].disabled = True
