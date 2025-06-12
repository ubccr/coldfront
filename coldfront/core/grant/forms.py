# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django import forms
from django.forms import ModelForm

from coldfront.core.grant.models import Grant
from coldfront.core.utils.common import import_from_settings

CENTER_NAME = import_from_settings("CENTER_NAME")


class GrantForm(ModelForm):
    class Meta:
        model = Grant
        exclude = [
            "project",
        ]
        labels = {
            "percent_credit": "Percent credit to {}".format(CENTER_NAME),
            "direct_funding": "Direct funding to {}".format(CENTER_NAME),
        }
        help_texts = {
            "percent_credit": "Percent credit as entered in the sponsored projects form for grant submission as financial credit to the department/unit in the credit distribution section. Enter only digits, decimals, percent symbols, or spaces.",
            "direct_funding": "Funds budgeted specifically for {} services, hardware, software, and/or personnel. Enter only digits, decimals, commas, dollar signs, or spaces.".format(
                CENTER_NAME
            ),
            "total_amount_awarded": "Enter only digits, decimals, commas, dollar signs, or spaces.",
        }

    def __init__(self, *args, **kwargs):
        super(GrantForm, self).__init__(*args, **kwargs)
        self.fields["funding_agency"].queryset = self.fields["funding_agency"].queryset.order_by("name")


class GrantDeleteForm(forms.Form):
    title = forms.CharField(max_length=255, disabled=True)
    grant_number = forms.CharField(max_length=30, required=False, disabled=True)
    grant_end = forms.CharField(max_length=150, required=False, disabled=True)
    selected = forms.BooleanField(initial=False, required=False)


class GrantDownloadForm(forms.Form):
    pk = forms.IntegerField(required=False, disabled=True)
    title = forms.CharField(required=False, disabled=True)
    project_pk = forms.IntegerField(required=False, disabled=True)
    pi_first_name = forms.CharField(required=False, disabled=True)
    pi_last_name = forms.CharField(required=False, disabled=True)
    role = forms.CharField(required=False, disabled=True)
    grant_pi = forms.CharField(required=False, disabled=True)
    total_amount_awarded = forms.FloatField(required=False, disabled=True)
    funding_agency = forms.CharField(required=False, disabled=True)
    grant_number = forms.CharField(required=False, disabled=True)
    grant_start = forms.DateField(required=False, disabled=True)
    grant_end = forms.DateField(required=False, disabled=True)
    percent_credit = forms.FloatField(required=False, disabled=True)
    direct_funding = forms.FloatField(required=False, disabled=True)
    selected = forms.BooleanField(initial=False, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["pk"].widget = forms.HiddenInput()
