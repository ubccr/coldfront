from django import forms
from django.shortcuts import get_object_or_404

from core.djangoapps.project.models import Project, ProjectUserRoleChoice


class ProjectSearchForm(forms.Form):
    """ Search form for the Project list page.
    """
    LAST_NAME = 'Last Name'
    USERNAME = 'Username'
    FIELD_OF_SCIENCE = 'Field of Science'

    last_name = forms.CharField(label=LAST_NAME, max_length=100, required=False)
    username = forms.CharField(label=USERNAME, max_length=100, required=False)
    field_of_science=forms.CharField(label=FIELD_OF_SCIENCE, max_length=100, required=False)


class ProjectAddUserForm(forms.Form):
    username = forms.CharField(max_length=150, disabled=True)
    first_name = forms.CharField(max_length=30, required=False, disabled=True)
    last_name = forms.CharField(max_length=150, required=False, disabled=True)
    email = forms.EmailField(max_length=100, required=False, disabled=True)
    source = forms.CharField(max_length=16, disabled=True)
    role = forms.ModelChoiceField(queryset=ProjectUserRoleChoice.objects.all(), empty_label=None)
    selected = forms.BooleanField(initial=False, required=False)


class ProjectAddUsersToSubscriptionForm(forms.Form):
    subscription = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, required=False)

    def __init__(self, request_user, project_pk, *args, **kwargs):
        super().__init__(*args, **kwargs)
        project_obj = get_object_or_404(Project, pk=project_pk)

        subscription_query_set = project_obj.subscription_set.filter(
            status__name__in=['Active', 'New', 'Pending'])
        subscription_choices = [(subscription.id, "%s (%s)" %(subscription.resources.first().name, subscription.resources.first().resource_type.name)) for subscription in subscription_query_set]
        subscription_choices.insert(0, ('__select_all__', 'Select All'))
        if subscription_query_set:
            self.fields['subscription'].choices = subscription_choices
            self.fields['subscription'].help_text = '<br/>Select subscriptions to add selected users to.'
        else:
            self.fields['subscription'].widget = forms.HiddenInput()


class ProjectDeleteUserForm(forms.Form):
    username = forms.CharField( max_length=150, disabled=True)
    first_name = forms.CharField(max_length=30, required=False, disabled=True)
    last_name = forms.CharField(max_length=150, required=False, disabled=True)
    email = forms.EmailField(max_length=100, required=False, disabled=True)
    role = forms.CharField(max_length=30, disabled=True)
    selected = forms.BooleanField(initial=False, required=False)


class ProjectUserUpdateForm(forms.Form):
    role = forms.ModelChoiceField(queryset = ProjectUserRoleChoice.objects.all(), empty_label=None)
    enable_notifications = forms.BooleanField(initial=False, required=False)
