from django import forms
from django.forms import ModelForm

from coldfront.core.research_output.models import ResearchOutput


class ResearchOutputForm(ModelForm):
    class Meta:
        model = ResearchOutput
        exclude = ['project', ]


class ResearchOutputReportForm(forms.Form):
    pk = forms.IntegerField(required=False, disabled=True)
    title = forms.CharField(required=False, disabled=True)
    description = forms.CharField(required=False, disabled=True)
    created_by = forms.CharField(required=False, disabled=True)
    project = forms.CharField(required=False, disabled=True)
    created = forms.DateField(required=False, disabled=True)
    selected = forms.BooleanField(initial=False, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['pk'].widget = forms.HiddenInput()
    


