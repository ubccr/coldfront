from datetime import date

from django import forms
from django.forms.widgets import RadioSelect
from django.core.exceptions import ValidationError

from coldfront.plugins.customizable_forms.validators import (ValidateNumberOfUsers,
                                                             ValidateAccountNumber,
                                                             ValidateDirectoryName,
                                                             ValidateDupDirectoryName)
from coldfront.plugins.customizable_forms.forms import BaseForm
from coldfront.plugins.ldap_user_info.utils import LDAPSearch, check_if_user_exists


class ComputeForm(BaseForm):
    YES_NO_CHOICES = (
        ('Yes', 'Yes'),
        ('No', 'No')
    )
    gpu_workflow = forms.ChoiceField(choices=YES_NO_CHOICES, widget=RadioSelect)
    dl_workflow = forms.ChoiceField(choices=YES_NO_CHOICES, widget=RadioSelect)
    applications_list = forms.CharField(max_length=128)

    def __init__(self, request_user, resource_attributes, project_obj, resource_obj, *args, **kwargs):
        super().__init__(request_user, resource_attributes, project_obj, resource_obj, *args, **kwargs)

        self.fields['applications_list'].widget.attrs.update({'placeholder': 'tensorflow,pytorch,etc.'})


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

    first_name = forms.CharField(max_length=40, disabled=True)
    last_name = forms.CharField(max_length=40, disabled=True)
    campus_affiliation = forms.ChoiceField(choices=CAMPUS_CHOICES)
    email = forms.EmailField(max_length=40, disabled=True)
    project_directory_name = forms.CharField(
        max_length=23, validators=[ValidateDirectoryName(), ValidateDupDirectoryName()]
    )
    storage_space = forms.IntegerField(min_value=1, max_value=30)
    start_date = forms.DateField(disabled=True)
    account_number = forms.CharField(max_length=9, initial='00-000-00', validators=[ValidateAccountNumber()])
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

    first_name = forms.CharField(max_length=40, disabled=True)
    last_name = forms.CharField(max_length=40, disabled=True)
    username = forms.CharField(max_length=40, disabled=True)
    email = forms.EmailField(max_length=50, disabled=True)
    phone_number = forms.CharField(max_length=12, required=False)
    primary_contact = forms.CharField(max_length=20, required=False)
    secondary_contact = forms.CharField(max_length=20, required=False)
    it_pro = forms.CharField(max_length=100, required=False)
    department_full_name = forms.CharField(max_length=30)
    department_short_name = forms.CharField(max_length=15, required=False, help_text='ex. UA-VPIT')
    department_primary_campus = forms.ChoiceField(choices=CAMPUS_CHOICES, required=False)
    group_name = forms.CharField(
        max_length=30, required=False, help_text='If applicable, enter the lab or group name of who will be primarily using this storage.'
    )
    storage_space = forms.IntegerField(min_value=1, help_text='Enter the size of storage needed in gigabytes (GB)')
    start_date = forms.DateField(widget=forms.TextInput(attrs={'class': 'datepicker'}), required=False)
    end_date = forms.DateField(widget=forms.TextInput(attrs={'class': 'datepicker'}), required=False)
    use_indefinitely = forms.BooleanField(initial=False, required=False)
    data_management_plan = forms.CharField(
        widget=forms.Textarea,
        help_text='<a href="#" data-toggle="modal" data-target="#id_data_best_practices_modal">Data Management Plan ideas and best practices</a>'    
    )
    admin_ads_group = forms.CharField(
        max_length=64,
        required=False,
        help_text=f'This ADS group will be used to identify user(s) who will have the storage ' 
        f'allocation "admin" role. This role can create directories at the allocation top-level '
        f'directory and assign permissions. Geode-Project allocations are a closed-first model. '
        f'Users in the "admin" role will need to create a directory and assign permissions to '
        f'users and groups in the "user" role ADS group (below). This must be an ADS group you or '
        f'your IT Pro creates/maintains.'
    )
    user_ads_group = forms.CharField(
        max_length=64,
        required=False,
        help_text=f'This ADS group will be used to identify user(s)/group(s) who will have the '
        f'storage allocation "user" role. This role will not be able to create directories at the '
        f'allocation top-level directory nor assign permissions. Geode-Project allocations are a '
        f'closed-first model. Users in the "admin" role will need to create a directory and assign '
        f'permissions to users and groups in this "user" role ADS group. The type of access a '
        f'"user" role has depends upon what permissions an "admin" grants. This must be an ADS '
        f'group you or your IT Pro creates/maintains.'
    )
    data_domains = forms.MultipleChoiceField(
        choices=DATA_DOMAIN_CHOICES,
        help_text='Select all domains of data which may be stored.',
        widget=forms.CheckboxSelectMultiple
    )
    fiscal_officer = forms.CharField(max_length=80)
    account_number = forms.CharField(max_length=9, help_text='Format: xx-xxx-xx', validators=[ValidateAccountNumber()])
    sub_account_number = forms.CharField(max_length=20, required=False)
    terms_of_service = forms.BooleanField(
        help_text='<a href="https://servicenow.iu.edu/kb?id=kb_article_view&sysparm_article=KB0023373" target="_blank" rel="noopener noreferrer">Geode-Project Terms of Service</a>'
    )
    data_management_responsibilities = forms.BooleanField(
        help_text='<a href="https://servicenow.iu.edu/kb?id=kb_article_view&sysparm_article=KB0023441" target="_blank" rel="noopener noreferrer">Data management responsibilities</a>'
    )
    confirm_best_practices = forms.BooleanField(
        help_text='<a href="#" data-toggle="modal" data-target="#id_data_best_practices_modal">Data Management Plan ideas and best practices</a>'
    )

    def __init__(self, request_user, resource_attributes, project_obj, resource_obj, *args, **kwargs):
        super().__init__(request_user, resource_attributes, project_obj, resource_obj, *args, **kwargs)

        self.fields['first_name'].initial = request_user.first_name
        self.fields['last_name'].initial = request_user.last_name
        self.fields['username'].initial = request_user.username
        self.fields['email'].initial = request_user.email

        self.fields['start_date'].widget.attrs.update({'placeholder': 'MM/DD/YYYY'})
        self.fields['end_date'].widget.attrs.update({'placeholder': 'MM/DD/YYYY'})

        for field in self.errors:
            self.fields[field].widget.attrs.update({'autofocus': ''})
            break

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        username_fields = ['primary_contact', 'secondary_contact', 'it_pro', 'fiscal_officer']
        ldap_conn = LDAPSearch()
        raise_error = False
        for username_field in username_fields:
            username = cleaned_data.get(username_field)
            if username:
                username_exists = check_if_user_exists(username, ldap_conn)
                if not username_exists:
                    self.add_error(username_field, 'This username does not exist')
                    raise_error = True

        if start_date and start_date < date.today():
            self.add_error('start_date', 'Must be today or later')
            raise_error = True

        if end_date and end_date < date.today():
            self.add_error('end_date', 'Must be today or later')
            raise_error = True

        if end_date and start_date:
            if end_date < start_date:
                self.add_error('end_date', 'Must be later than the start date')
                raise_error = True

        if raise_error:
            raise ValidationError('Please correct the error(s) below')
