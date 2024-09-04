from datetime import date

from django import forms
from django.forms.widgets import RadioSelect
from django.conf import settings
from django.core.exceptions import ValidationError

from coldfront.plugins.customizable_forms.validators import (ValidateNumberOfUsers,
                                                             ValidateAccountNumber,
                                                             ValidateDirectoryName)
from coldfront.plugins.customizable_forms.forms import BaseForm

class PositConnectForm(BaseForm):
    YES_NO_CHOICES = (
        ('Yes', 'Yes'),
        ('No', 'No')
    )
    USE_TYPE_CHOICES = (
        ('Research', 'Research'),
        ('Class', 'Class')
    )
    use_type = forms.ChoiceField(choices=USE_TYPE_CHOICES, required=True, widget=RadioSelect)
    will_exceed_limit = forms.ChoiceField(choices=YES_NO_CHOICES, required=True, widget=RadioSelect)

    def __init__(self, request_user, resource_attributes, project_obj, resource_obj, *args, **kwargs):
        super().__init__(request_user, resource_attributes, project_obj, resource_obj, *args, **kwargs)
        limit_obj = resource_obj.resourceattribute_set.filter(resource_attribute_type__name = 'user_limit')
        if limit_obj.exists():
            limit = int(limit_obj[0].value)
            count_start = 1
            if request_user != project_obj.pi:
                count_start += 1
            self.fields['users'].validators = [ValidateNumberOfUsers(limit, count_start)]


class SlateProjectForm(BaseForm):
    YES_NO_CHOICES = (
        ('Yes', 'Yes'),
        ('No', 'No')
    )
    CAMPUS_CHOICES = (
        ('', ''),
        ('BL', 'IU Bloomington'),
        ('IN', 'IUPUI (Indianapolis)'),
        ('CO', 'IUPUC (Columbus)'),
        ('EA', 'IU East (Richmond)'),
        ('FW', 'IU Fort Wayne'),
        ('CO', 'IU Kokomo'),
        ('NW', 'IU Northwest (Gary)'),
        ('SB', 'IU South Bend'),
        ('SE', 'IU Southeast (New Albany)'),
        ('OR', 'Other')
    )

    first_name = forms.CharField(max_length=40)
    last_name = forms.CharField(max_length=40)
    campus_affiliation = forms.ChoiceField(choices=CAMPUS_CHOICES)
    email = forms.EmailField(max_length=40)
    url = forms.CharField(max_length=50, required=False)
    project_directory_name = forms.CharField(max_length=10, validators=[ValidateDirectoryName()])
    storage_space = forms.IntegerField(min_value=0)
    start_date = forms.DateField(widget=forms.TextInput(attrs={'class': 'datepicker'}))
    faculty_email = forms.EmailField(max_length=40, help_text='If applicable', required=False)
    store_ephi = forms.ChoiceField(choices=YES_NO_CHOICES, widget=RadioSelect)
    account_number = forms.CharField(
        max_length=9,
        help_text='Required for requests of 15 TB or greater',
        validators=[ValidateAccountNumber()],
        required=False
    )

    def __init__(self, request_user, resource_attributes, project_obj, resource_obj, *args, **kwargs):
        super().__init__(request_user, resource_attributes, project_obj, resource_obj, *args, **kwargs)

        self.fields['first_name'].initial = request_user.first_name
        self.fields['last_name'].initial = request_user.last_name
        self.fields['email'].initial = request_user.email

        self.fields['url'].widget.attrs.update({'placeholder': 'http://'})
        self.fields['project_directory_name'].widget.attrs.update({'placeholder': 'example_A-Za-z0-9'})
        self.fields['storage_space'].widget.attrs.update({'placeholder': '0'})
        self.fields['start_date'].widget.attrs.update({'placeholder': 'mm/dd/yyy'})
        self.fields['faculty_email'].widget.attrs.update({'placeholder': 'address@iu.edu'})

        if 'coldfront.plugins.ldap_user_info' in settings.INSTALLED_APPS:
            from coldfront.plugins.ldap_user_info.utils import get_user_info
            attributes = get_user_info(request_user.username, ['ou'])
            if attributes.get('ou'):
                self.fields['campus_affiliation'].initial = attributes['ou'][0]

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('storage_space') > 15:
            account_number = cleaned_data.get('account_number')
            if account_number is not None and not account_number:
                self.add_error('account_number', 'This field is required')
                raise ValidationError('Please correct the error below')

        if cleaned_data.get('start_date') <= date.today():
            self.add_error('start_date', 'Must be later than today')
            raise ValidationError('Please correct the error below')


class GeodeProjectForm(BaseForm):
    DATA_DOMAIN_CHOICES = (
        ('Advancement', 'Advancement'),
        ('Employee', 'Employee'),
        ('Facilities', 'Facilities'),
        ('Financial', 'Financial'),
        ('Health', 'Health'),
        ('International', 'International'),
        ('Learning Management', 'Learning Management'),
        ('Library', 'Library'),
        ('Purchasing', 'Purchasing'),
        ('Research', 'Research'),
        ('Student', 'Student'),
        ('Travel', 'Travel')
    )
    CAMPUS_CHOICES = (
        ('', ''),
        ('IUB', 'IUB'),
        ('IUN', 'IUN'),
        ('IUE', 'IUE'),
        ('IUK', 'IUK'),
        ('IUNW', 'IUNW'),
        ('IUSB', 'IUSB'),
        ('IUSE', 'IUSE'),
        ('IUFW', 'IUFW'),
        ('IUPUC', 'IUPUC'),
    )

    name = forms.CharField(max_length=80)
    username = forms.CharField(max_length=40)
    email = forms.EmailField(max_length=50)
    phone_number = forms.CharField(max_length=12, required=False)
    primary_contact = forms.CharField(max_length=20, required=False)
    secondary_contact = forms.CharField(max_length=20, required=False)
    it_pros = forms.CharField(max_length=100, required=False)
    department_full_name = forms.CharField(max_length=30)
    department_short_name = forms.CharField(max_length=15, required=False)
    department_primary_campus = forms.ChoiceField(choices=CAMPUS_CHOICES, required=False)
    group_name = forms.CharField(max_length=30, required=False)
    storage_space = forms.IntegerField(min_value=1)
    start_date = forms.DateField(widget=forms.TextInput(attrs={'class': 'datepicker'}), required=False)
    end_date = forms.DateField(widget=forms.TextInput(attrs={'class': 'datepicker'}), required=False)
    use_indefinitely = forms.BooleanField(required=False)
    data_management_plan = forms.CharField(widget=forms.Textarea)
    admin_ads_group = forms.CharField(max_length=64, required=False)
    user_ads_group = forms.CharField(max_length=64, required=False)
    data_domains = forms.MultipleChoiceField(choices=DATA_DOMAIN_CHOICES)
    fiscal_officer = forms.CharField(max_length=80)
    account_number = forms.CharField(max_length=9, validators=[ValidateAccountNumber()])
    sub_account_number = forms.CharField(max_length=20, required=False)
    terms_of_service = forms.BooleanField()
    data_management_responsibilities = forms.BooleanField()

    def __init__(self, request_user, resource_attributes, project_obj, resource_obj, *args, **kwargs):
        super().__init__(request_user, resource_attributes, project_obj, resource_obj, *args, **kwargs)

        self.fields['name'].initial = f'{request_user.first_name} {request_user.last_name}'
        self.fields['username'].initial = request_user.username
        self.fields['email'].initial = request_user.email

        # self.fields['start_date'].widget.attrs.update({'placeholder': 'mm/dd/yyy'})
        # self.fields['end_date'].widget.attrs.update({'placeholder': 'mm/dd/yyy'})

    def clean(self):
        pass