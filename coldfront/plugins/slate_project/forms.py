from django import forms


class SlateProjectSearchForm(forms.Form):
    GID = 'Slate Project GID'
    gid = forms.IntegerField(label=GID)