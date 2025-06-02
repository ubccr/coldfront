# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django import forms
from django.db.models.functions import Lower

from coldfront.core.resource.models import ResourceAttribute


class ResourceSearchForm(forms.Form):
    """Search form for the Resource list page."""

    model = forms.CharField(label="Model", max_length=100, required=False)
    serialNumber = forms.CharField(label="Serial Number", max_length=100, required=False)
    vendor = forms.CharField(label="Vendor", max_length=100, required=False)
    installDate = forms.DateField(
        label="Install Date", widget=forms.DateInput(attrs={"class": "datepicker"}), required=False
    )
    serviceStart = forms.DateField(
        label="Service Start", widget=forms.DateInput(attrs={"class": "datepicker"}), required=False
    )
    serviceEnd = forms.DateField(
        label="Service End", widget=forms.DateInput(attrs={"class": "datepicker"}), required=False
    )
    warrantyExpirationDate = forms.DateField(
        label="Warranty Expiration Date", widget=forms.DateInput(attrs={"class": "datepicker"}), required=False
    )
    show_allocatable_resources = forms.BooleanField(initial=False, required=False)


class ResourceAttributeDeleteForm(forms.Form):
    pk = forms.IntegerField(required=False, disabled=True)
    name = forms.CharField(max_length=150, required=False, disabled=True)
    value = forms.CharField(max_length=150, required=False, disabled=True)
    selected = forms.BooleanField(initial=False, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["pk"].widget = forms.HiddenInput()


class ResourceAttributeCreateForm(forms.ModelForm):
    class Meta:
        model = ResourceAttribute
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(ResourceAttributeCreateForm, self).__init__(*args, **kwargs)
        self.fields["resource_attribute_type"].queryset = self.fields["resource_attribute_type"].queryset.order_by(
            Lower("name")
        )
