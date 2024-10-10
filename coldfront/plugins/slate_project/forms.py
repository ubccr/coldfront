from django import forms


class SlateProjectSearchForm(forms.Form):
    GID = 'Slate Project GID'
    gid = forms.CharField(label=GID, max_length=5)