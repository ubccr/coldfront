from django import forms
from django.forms.widgets import RadioSelect

from coldfront.plugins.customizable_forms.validators import ValidateNumberOfUsers
from coldfront.plugins.customizable_forms.forms import BaseForm


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
