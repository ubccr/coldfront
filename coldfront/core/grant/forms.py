from re import T
from django import forms
from django.forms import ModelForm
from django.shortcuts import get_object_or_404

from coldfront.core.grant.models import Grant
from coldfront.core.utils.common import import_from_settings

CENTER_NAME = import_from_settings('CENTER_NAME')


class GrantForm(ModelForm):
    class Meta:
        model = Grant
        exclude = ['project', ]
        labels = {
            'percent_credit': 'Percent credit to {}'.format(CENTER_NAME),
            'direct_funding': 'Direct funding to {}'.format(CENTER_NAME)
        }
        help_texts = {
            'percent_credit': 'Percent credit as entered in the sponsored projects form for grant submission as financial credit to the department/unit in the credit distribution section',
            'direct_funding': 'Funds budgeted specifically for {} services, hardware, software, and/or personnel'.format(CENTER_NAME)
        }

class OrcidImportGrantResultForm(forms.Form):
    title = forms.CharField(max_length=1024, disabled=True)
    grant_number = forms.CharField(
        max_length=30, disabled=True)
    total_amount_awarded = forms.FloatField(disabled=True)
    amount_awarded_currency = forms.CharField(max_length=3, disabled=True)
    role = forms.MultipleChoiceField(choices=Grant.ROLE_CHOICES, initial="PI")
    grant_pi_full_name=forms.CharField(max_length=255, required=False)
    grant_start = forms.CharField(max_length=150, disabled=True)
    grant_end = forms.CharField(max_length=150, disabled=True)
    funding_agency = forms.CharField(max_length=1024, disabled=True)
    percent_credit = forms.FloatField(max_value=100, min_value=0, required=False, initial=0)
    direct_funding = forms.FloatField(required=False, initial=0)
    STATUS_CHOICES = (
        ('Active', 'Active'),
        ('Archived', 'Archived'),
        ('Pending', 'Pending'),
    )
    status = forms.MultipleChoiceField(choices=STATUS_CHOICES, initial='Active')
    unique_id = forms.CharField(max_length=255, disabled=True)
    source_pk = forms.IntegerField(widget=forms.HiddenInput(), disabled=True, required=False)
    selected = forms.BooleanField(initial=False, required=False)

class GrantDeleteForm(forms.Form):
    title = forms.CharField(max_length=255, disabled=True)
    grant_number = forms.CharField(
        max_length=30, required=False, disabled=True)
    grant_end = forms.CharField(max_length=150, required=False, disabled=True)
    selected = forms.BooleanField(initial=False, required=False)
