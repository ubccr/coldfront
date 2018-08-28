from django import forms
from django.shortcuts import get_object_or_404
from django.forms import ModelForm
from common.djangolibs.utils import import_from_settings
from core.djangoapps.grant.models import Grant


class GrantForm(ModelForm):
    class Meta:
        model = Grant
        exclude = ['project', ]


class GrantDeleteUserForm(forms.Form):
    title = forms.CharField(max_length=150, disabled=True)
    grant_number = forms.CharField(max_length=30, required=False, disabled=True)
    grant_end = forms.CharField(max_length=150, required=False, disabled=True)
    selected = forms.BooleanField(initial=False, required=False)
