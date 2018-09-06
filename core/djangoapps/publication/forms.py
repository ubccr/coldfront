from django import forms
from core.djangoapps.publication.models import PublicationSource


class PublicationSearchForm(forms.Form):
    source = forms.ModelChoiceField(queryset=PublicationSource.objects.all(), empty_label=None)
    unique_id = forms.CharField(max_length=100, required=True)


class PublicationDeleteForm(forms.Form):
    title = forms.CharField(max_length=255, disabled=True)
    year = forms.CharField(max_length=30, disabled=True)
    selected = forms.BooleanField(initial=False, required=False)
