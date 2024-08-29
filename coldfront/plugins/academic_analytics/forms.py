from django import forms


class PublicationForm(forms.Form):
    title = forms.CharField(max_length=1024, disabled=True)
    author = forms.CharField(disabled=True)
    year = forms.IntegerField(disabled=True)
    journal = forms.CharField(max_length=1024, disabled=True)
    unique_id = forms.CharField(max_length=255, disabled=True, required=False)
    add = forms.BooleanField(initial=False, required=False)