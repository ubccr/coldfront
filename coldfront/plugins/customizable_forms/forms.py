from django import forms
from django.shortcuts import get_object_or_404
from django.forms.widgets import RadioSelect
from django.conf import settings

from coldfront.core.project.models import Project
from coldfront.core.allocation.utils import get_user_resources
from coldfront.plugins.customizable_forms.validators import ValidateNumberOfUsers


class BaseAllocationForm(forms.Form):
    resource = forms.ChoiceField(choices=())
    users = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, required=False)

    def __init__(self, request_user, project_pk, *args, after_project_creation=False, **kwargs):
        super().__init__(*args, **kwargs)

        RESOURCE_CHOICES = [(None, 'Please select a resource...')]
        for resource in get_user_resources(request_user):
            RESOURCE_CHOICES.append((resource.pk, resource))

        project_obj = get_object_or_404(Project, pk=project_pk)
        self.project_obj = project_obj
        self.request_user = request_user
        self.fields['resource'].choices = RESOURCE_CHOICES
        user_query_set = project_obj.projectuser_set.select_related('user').filter(
            status__name__in=['Active', ]).order_by("user__username")
        user_query_set = user_query_set.exclude(user__in=[project_obj.pi, request_user])

        if user_query_set:
            self.fields['users'].choices = ((user.user.username, "%s %s (%s)" % (
                user.user.first_name, user.user.last_name, user.user.username)) for user in user_query_set)
            self.fields['users'].help_text = '<br/>Select users in your project to add to this allocation.'
        else:
            self.fields['users'].widget = forms.HiddenInput()

###################


class BaseForm(forms.Form):
    resource = forms.IntegerField(disabled=True, widget=forms.HiddenInput())
    users = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, required=False)

    def __init__(self, request_user, resource_attributes, project_obj, resource_obj, *args, run_form_setup=True, **kwargs):
        super().__init__(*args, **kwargs)
        if run_form_setup:
            self.set_up_fields(request_user, resource_attributes, project_obj, resource_obj)

    def set_up_users_field(self, request_user, project_obj, resource_obj):
        user_query_set = project_obj.projectuser_set.select_related('user').filter(
            status__name__in=['Active', ]).order_by("user__username")
        user_query_set = user_query_set.exclude(user__in=[project_obj.pi, request_user])

        if user_query_set:
            self.fields['users'].choices = ((user.user.username, "%s %s (%s)" % (
                user.user.first_name, user.user.last_name, user.user.username)) for user in user_query_set)
            self.fields['users'].help_text = '<br/>Select users in your project to add to this allocation.'
        else:
            self.fields['users'].widget = forms.HiddenInput()

        self.fields['resource'].initial = resource_obj.pk

        # Move users field to the bottom of the form
        self.fields['users'] = self.fields.pop('users')

    def set_up_fields(self, request_user, resource_attributes, project_obj, resource_obj, ):
        for resource_attribute in resource_attributes:
            name = resource_attribute.resource_attribute_type.name
            if 'label' in name:
                name = name[:-len('_label')]
                if self.fields.get(name) is not None:
                    self.fields[name].label = '<strong>' + resource_attribute.value + '</strong>'
            else:
                if self.fields.get(name) is not None:
                    self.fields[name].initial = resource_attribute.value

        self.set_up_users_field(request_user, project_obj, resource_obj)


class GenericForm(BaseForm):
    def __init__(self, request_user, resource_attributes, project_obj, resource_obj, *args, **kwargs):
        super().__init__(request_user, resource_attributes, project_obj, resource_obj, *args, run_form_setup = False, **kwargs)
        YES_NO_CHOICES = (
            ('Yes', 'Yes'),
            ('No', 'No')
        )

        new_fields = {}
        for resource_attribute in resource_attributes:
            name = resource_attribute.resource_attribute_type.name
            if 'label' in name:
                new_fields[name[:-len('_label')]] = {'label': resource_attribute.value}

        for resource_attribute in resource_attributes:
            name = resource_attribute.resource_attribute_type.name
            attribute_type = resource_attribute.resource_attribute_type.attribute_type.name
            new_field = new_fields.get(name)
            if new_field is not None:
                new_fields[name] = {
                    'type': attribute_type,
                    'default': resource_attribute.value,
                    'label': new_field.get('label')
                }

        for name, info in new_fields.items():
            attribute_type = info.get('type')
            label = f'<strong>{info.get("label")}</strong>'
            if attribute_type == 'Text':
                self.fields[name[:-len('_label')]] = forms.CharField(required=True, label=label)
            elif attribute_type == 'Yes/No':
                self.fields[name[:-len('_label')]] = forms.ChoiceField(
                    choices=YES_NO_CHOICES, required=True, label=label, widget=RadioSelect
                )

        self.set_up_users_field(request_user, project_obj, resource_obj)


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

