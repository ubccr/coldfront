from django import forms


class SlateProjectSearchForm(forms.Form):
    SLATE_PROJECT = 'Slate Project'
    slate_project = forms.CharField(label=SLATE_PROJECT, min_length=2, max_length=30)
