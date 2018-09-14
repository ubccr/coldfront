from django import forms

from core.djangoapps.publication.models import PublicationSource


class PublicationSearchForm(forms.Form):
    unique_id = forms.CharField(label='Unique ID', max_length=100, required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['unique_id'].help_text = '<br/>Enter unique ID such as DOI or Bibliographic Code'


class PublicationDeleteForm(forms.Form):
    title = forms.CharField(max_length=255, disabled=True)
    year = forms.CharField(max_length=30, disabled=True)
    selected = forms.BooleanField(initial=False, required=False)
