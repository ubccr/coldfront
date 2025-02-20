from datetime import date

from django import forms
from django.forms.widgets import RadioSelect
from coldfront.plugins.slate_project.validators import ValidateDirectoryName, ValidateDupDirectoryName, ValidateAccountNumber


class SlateProjectSearchForm(forms.Form):
    SLATE_PROJECT = 'Slate Project'
    slate_project = forms.CharField(label=SLATE_PROJECT, min_length=2, max_length=30)


class SlateProjectForm:
    YES_NO_CHOICES = (
        ('Yes', 'Yes'),
        ('No', 'No')
    )
    CAMPUS_CHOICES = (
        ('', ''),
        ('BL', 'BL'),
        ('IN', 'IN'),
        ('CO', 'CO'),
        ('EA', 'EA'),
        ('FW', 'FW'),
        ('KO', 'KO'),
        ('NW', 'NW'),
        ('SB', 'SB'),
        ('SE', 'SE'),
    )
    STORAGE_QUANTITY_CHOICES = [
        (num, num) for num in range(1, 31)
    ]
    STORAGE_QUANTITY_CHOICES = [('', '')] + STORAGE_QUANTITY_CHOICES
    DATE_RANGES = (
        ('', ''),
        ('<1 year', '<1 year'),
        ('1-3 years', '1-3 years'),
        ('3-5 years', '3-5 years'),
        ('+5 years', '+5 years')
    )

    first_name = forms.CharField(max_length=40, disabled=True)
    last_name = forms.CharField(max_length=40, disabled=True)
    campus_affiliation = forms.ChoiceField(choices=CAMPUS_CHOICES)
    email = forms.EmailField(max_length=40, disabled=True)
    project_directory_name = forms.CharField(
        max_length=23, validators=[ValidateDirectoryName(), ValidateDupDirectoryName()]
    )
    description = forms.CharField(widget=forms.Textarea)
    data_generation = forms.CharField(max_length=128)
    data_protection = forms.CharField(max_length=128)
    data_computational_lifetime = forms.ChoiceField(choices=DATE_RANGES)
    expected_project_lifetime = forms.ChoiceField(choices=DATE_RANGES)
    storage_space = forms.IntegerField(min_value=1, max_value=30, widget=forms.Select(choices=STORAGE_QUANTITY_CHOICES))
    start_date = forms.DateField(disabled=True)
    account_number = forms.CharField(max_length=9, validators=[ValidateAccountNumber()], required=False)
    store_ephi = forms.ChoiceField(choices=YES_NO_CHOICES, widget=RadioSelect)

    def __init__(self, request_user, resource_attributes, project_obj, resource_obj, *args, **kwargs):
        super().__init__(request_user, resource_attributes, project_obj, resource_obj, *args, **kwargs)

        self.fields['first_name'].initial = request_user.first_name
        self.fields['last_name'].initial = request_user.last_name
        self.fields['email'].initial = request_user.email
        self.fields['start_date'].initial = date.today()

        self.fields['project_directory_name'].widget.attrs.update({'placeholder': 'example_A-Za-z0-9'})

        for field in self.errors:
            self.fields[field].widget.attrs.update({'autofocus': ''})
            break
