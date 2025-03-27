from django import forms

from coldfront.core.allocation.models import (
    AllocationStatusChoice,
)

from django.db.models.functions import Lower


class AllocationTableSearchForm(forms.Form):
    pi_last_name = forms.CharField(label="PI Surname", max_length=100, required=False)

    pi_first_name = forms.CharField(
        label="PI Given Name", max_length=100, required=False
    )

    status = forms.ModelMultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        queryset=AllocationStatusChoice.objects.all().order_by(Lower("name")),
        required=False,
    )

    department_number = forms.CharField(
        label="Department Number", max_length=100, required=False
    )

    itsd_ticket = forms.CharField(label="ITSD Ticket", max_length=100, required=False)

    no_grouping = forms.BooleanField(
        label="No Grouping",
        initial=False,
        required=False,
    )
