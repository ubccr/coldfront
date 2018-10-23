from django import forms
from django.forms import ModelForm
from django.shortcuts import get_object_or_404

from coldfront.core.utils.common import import_from_settings
from coldfront.core.grant.models import Grant


class GrantForm(ModelForm):
    class Meta:
        model = Grant
        exclude = ['project', ]


class GrantDeleteForm(forms.Form):
    title = forms.CharField(max_length=150, disabled=True)
    grant_number = forms.CharField(max_length=30, required=False, disabled=True)
    grant_end = forms.CharField(max_length=150, required=False, disabled=True)
    selected = forms.BooleanField(initial=False, required=False)
