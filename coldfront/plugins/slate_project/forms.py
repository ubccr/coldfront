from django import forms


class SlateProjectSearchForm(forms.Form):
    SLATE_PROJECT = 'Slate Project'
    slate_project = forms.CharField(label=SLATE_PROJECT, max_length=30)