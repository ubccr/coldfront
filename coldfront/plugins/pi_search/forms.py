from django import forms


class PISearchForm(forms.Form):
    PI_SEARCH = 'PI Username'
    pi_search = forms.CharField(label=PI_SEARCH, max_length=100)