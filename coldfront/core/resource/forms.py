from django import forms


class ResourceSearchForm(forms.Form):
    """ Search form for the Resource list page.
    """
    LAST_NAME = 'Last Name'
    USERNAME = 'Username'
    FIELD_OF_SCIENCE = 'Field of Science'

    last_name = forms.CharField(
        label=LAST_NAME, max_length=100, required=False)
    username = forms.CharField(label=USERNAME, max_length=100, required=False)
    field_of_science = forms.CharField(
        label=FIELD_OF_SCIENCE, max_length=100, required=False)
    show_all_projects = forms.BooleanField(initial=False, required=False)


class ResourceAttributeDeleteForm(forms.Form):
    pk = forms.IntegerField(required=False, disabled=True)
    name = forms.CharField(max_length=150, required=False, disabled=True)
    value = forms.CharField(max_length=150, required=False, disabled=True)
    selected = forms.BooleanField(initial=False, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['pk'].widget = forms.HiddenInput()