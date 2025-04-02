from django import forms
from django.forms.widgets import RadioSelect
from django.utils.html import format_html
from crispy_forms.helper import FormHelper


class DisableableCheckboxSelectMultiple(forms.CheckboxSelectMultiple):

    def __init__(self, *args, **kwargs):
        self.disable_choices = kwargs.pop('disable_choices', {})
        super().__init__(*args, **kwargs)

    def create_option(self, name, value, *args, **kwargs):
        option = super().create_option(name, value, *args, **kwargs)
        if value in self.disable_choices.keys():
            option['attrs']['disabled'] = True
            label = format_html(
                f'{option["label"]} '
                f'<a href="#" data-toggle="popover" title="Cannot Add" data-trigger="hover" data-content="{self.disable_choices[value]}">'
                f'<span class="badge badge-warning">'
                f'<i class="fas fa-exclamation-circle" aria-hidden="true"></i>'
                f'<span class="sr-only">{self.disable_choices[value]}</span>'
                f'</span>'
                f'</a>'
            )
            option['label'] = label
        return option


class BaseForm(forms.Form):
    resource = forms.IntegerField(disabled=True, widget=forms.HiddenInput())
    users = forms.MultipleChoiceField(widget=DisableableCheckboxSelectMultiple, required=False)

    def __init__(self, request_user, resource_attributes, project_obj, resource_obj, *args, run_form_setup=True, **kwargs):
        super().__init__(*args, **kwargs)
        if run_form_setup:
            self.set_up_fields(request_user, resource_attributes, project_obj, resource_obj)

        self.helper = FormHelper()

    def set_up_users_field(self, request_user, project_obj, resource_obj):
        user_query_set = project_obj.projectuser_set.select_related('user').filter(
            status__name__in=['Active', ]).order_by("user__username")
        user_query_set = user_query_set.exclude(user__in=[project_obj.pi, request_user])

        if user_query_set:
            disable_choices = {}
            results = resource_obj.check_users_accounts([user.user.username for user in user_query_set])
            for username, result in results.items():
                if not result.get('exists'):
                    message = ''
                    if result.get('reason') == 'no_account':
                        message = 'No IU account'
                    elif result.get('reason') == 'no_resource_account':
                        message = f'No {resource_obj.name} account'
                    
                    disable_choices[username] = message

            self.fields['users'].choices = ((user.user.username, "%s %s (%s)" % (
                user.user.first_name, user.user.last_name, user.user.username)) for user in user_query_set)
            self.fields['users'].help_text = (f'<br/>Select users in your project to add to this allocation. '
                                              f'If a user cannot be added hover over the icon next to their username to see why.')
            if disable_choices:
                self.fields['users'].widget.disable_choices = disable_choices
        else:
            self.fields['users'].widget = forms.HiddenInput()

        self.fields['resource'].initial = resource_obj.pk

        # Move users field to the bottom of the form
        self.fields['users'] = self.fields.pop('users')

    def set_up_fields(self, request_user, resource_attributes, project_obj, resource_obj):
        for resource_attribute in resource_attributes:
            name = resource_attribute.resource_attribute_type.name
            if 'label' in name:
                name = name[:-len('_label')]
                if self.fields.get(name) is not None:
                    self.fields[name].label = resource_attribute.value
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
            label = info.get("label")
            if attribute_type == 'Text':
                self.fields[name[:-len('_label')]] = forms.CharField(required=True, label=label)
            elif attribute_type == 'Yes/No':
                self.fields[name[:-len('_label')]] = forms.ChoiceField(
                    choices=YES_NO_CHOICES, required=True, label=label, widget=RadioSelect
                )

        self.set_up_users_field(request_user, project_obj, resource_obj)
