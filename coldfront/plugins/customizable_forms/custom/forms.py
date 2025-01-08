from django import forms
from django.forms.widgets import RadioSelect
from django.core.exceptions import ValidationError

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


class OptionalChoiceWidget(forms.MultiWidget):
    def decompress(self, value):
        if value:
            if value in [choice[0] for choice in self.widgets[0].choices]:
                 return [value, '']
            else:
                 return ['', value]
        return ['', '']


class OptionalChoiceField(forms.MultiValueField):
    def __init__(self, choices, max_length = 128, *args, **kwargs):
        fields = (forms.ChoiceField(choices=choices, widget=RadioSelect, required=False),
                  forms.CharField(max_length=max_length, label='Please specify:', required=False))
        self.widget = OptionalChoiceWidget(widgets=[field.widget for field in fields])
        super().__init__(fields=fields, *args, **kwargs)

    def compress(self, data_list):
        if not data_list:
            return ''

        if data_list[0] == 'Other':
            if not data_list[1]:
                raise ValidationError('You need to fill in this field')
            return data_list[1]

        return data_list[0] or data_list[1]


class QuartzHopperForm(BaseForm):
    YES_MAYBE_NO_CHOICES = (
        ('No', 'No'),
        ('Sometimes', 'Sometimes'),
        ('Yes', 'Yes')
    )

    WORKFLOW_NEEDS_CHOICES = (
        ('Does not fit on single GPU', 'Workflow does not fit on a single GPU'),
        ('Faster performance', 'Faster performance'),
        ('Other', 'Other')
    )

    GPU_MEMORY_CHOICES = (
        ('Do not know', 'I dont know'),
        ('<40GB', 'Yes, less than 40GB'),
        ('40-80GB', 'Yes, between 40-80GB'),
        ('80-320GB', 'Yes, between 80-320GB'),
        ('>320GB', 'Yes, greater than 320GB'),
    )

    multi_gpu_workflow = forms.ChoiceField(choices=YES_MAYBE_NO_CHOICES, widget=RadioSelect)
    workflow_needs = OptionalChoiceField(choices=WORKFLOW_NEEDS_CHOICES, required=False)
    gpu_memory = forms.ChoiceField(choices=GPU_MEMORY_CHOICES, widget=RadioSelect)
    applications_list = forms.CharField(max_length=128)


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
