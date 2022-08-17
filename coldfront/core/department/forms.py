
from django import forms

class DepartmentSearchForm(forms.Form):
    """ Search form for the Project list page.
    """

    name = forms.CharField(label='Department Name', max_length=100, required=False)
    field_of_science = forms.CharField(
        label='Field of Science', max_length=100, required=False)
    show_all_departments = forms.BooleanField(initial=False, required=False)
