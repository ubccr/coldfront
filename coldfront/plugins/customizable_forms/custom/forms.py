from django import forms
from django.forms.widgets import RadioSelect
from django.conf import settings

from coldfront.plugins.customizable_forms.validators import ValidateNumberOfUsers
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
    project_directory_name = forms.CharField(max_length=10)
    storage_space = forms.IntegerField()
    start_date = forms.DateField(widget=forms.TextInput(attrs={'class': 'datepicker'}))
    faculty_email = forms.EmailField(max_length=40)
    store_ephi = forms.ChoiceField(choices=YES_NO_CHOICES, widget=RadioSelect)
    account_number = forms.CharField(max_length=9, validators=[])

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