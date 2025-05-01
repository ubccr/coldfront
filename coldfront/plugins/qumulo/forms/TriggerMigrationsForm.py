from django import forms


class TriggerMigrationsForm(forms.Form):
    allocation_name_search = forms.CharField(
        label="Allocation Name",
        max_length=100,
        required=True,
        help_text="Type the allocation name here!",
    )
