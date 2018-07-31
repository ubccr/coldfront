from django import forms
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404

from common.djangolibs.utils import import_from_settings
from core.djangoapps.project.models import Project
from core.djangoapps.resources.models import Resource, ResourceType
from core.djangoapps.subscription.models import (Subscription,
                                                 SubscriptionStatusChoice)
from core.djangoapps.subscription.utils import get_user_resources

EMAIL_DIRECTOR_PENDING_SUBSCRIPTION_EMAIL = import_from_settings('EMAIL_DIRECTOR_PENDING_SUBSCRIPTION_EMAIL')


class SubscriptionForm(forms.Form):
    resource = forms.ModelChoiceField(queryset=None, empty_label=None)
    justification = forms.CharField(widget=forms.Textarea)
    quantity = forms.IntegerField(required=True)
    users = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, required=False)

    def __init__(self, request_user, project_pk, *args, **kwargs):
        super().__init__(*args, **kwargs)
        project_obj = get_object_or_404(Project, pk=project_pk)
        self.fields['resource'].queryset = get_user_resources(request_user)
        self.fields['quantity'].initial = 1
        user_query_set = project_obj.projectuser_set.select_related('user').filter(
            status__name__in=['Active', 'Pending Add']).exclude(user=request_user)
        if user_query_set:
            self.fields['users'].choices = ((user.user.username, "%s %s (%s)" % (user.user.first_name, user.user.last_name, user.user.username)) for user in user_query_set)
            self.fields['users'].help_text = '<br/>Select users in your project to add to this subscription.'
        else:
            self.fields['users'].widget = forms.HiddenInput()

        self.fields['justification'].help_text = '<br/>Justification for requesting this subscription.'


class SubscriptionAddUserForm(forms.Form):
    username = forms.CharField(max_length=150, disabled=True)
    first_name = forms.CharField(max_length=30, required=False, disabled=True)
    last_name = forms.CharField(max_length=150, required=False, disabled=True)
    email = forms.EmailField(max_length=100, required=False, disabled=True)
    selected = forms.BooleanField(initial=False, required=False)


class SubscriptionDeleteUserForm(forms.Form):
    username = forms.CharField(max_length=150, disabled=True)
    first_name = forms.CharField(max_length=30, required=False, disabled=True)
    last_name = forms.CharField(max_length=150, required=False, disabled=True)
    email = forms.EmailField(max_length=100, required=False, disabled=True)
    selected = forms.BooleanField(initial=False, required=False)


class SubscriptionSearchForm(forms.Form):
    project = forms.CharField(label='Project', max_length=100, required=False)
    pi = forms.CharField(label='PI', max_length=100, required=False)
    resource_type = forms.ModelChoiceField(
        label='Resource Type',
        queryset=ResourceType.objects.all().order_by('name'),
        required=False)
    resource_name = forms.ModelMultipleChoiceField(
        label='Resource Name',
        queryset=Resource.objects.all().order_by('name'),
        required=False)
    active_until = forms.DateField(
        label='Active Until',
        widget=forms.DateInput(attrs={'class': 'datepicker'}),
        required=False)
    active_from_now_until_date = forms.DateField(
        label='Active From Now Until Date',
        widget=forms.DateInput(attrs={'class': 'datepicker'}),
        required=False)
    status = forms.ModelMultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        queryset=SubscriptionStatusChoice.objects.all().order_by('name'),
        required=False)


class SubscriptionEmailForm(forms.Form):
    email_body = forms.CharField(
        required=True,
        widget=forms.Textarea
    )

    def __init__(self, pk, *args, **kwargs):
        super().__init__(*args, **kwargs)
        subscription_obj = get_object_or_404(Subscription, pk=int(pk))
        self.fields['email_body'].initial = 'Dear {} {} \n{}'.format(subscription_obj.project.pi.first_name, subscription_obj.project.pi.last_name, EMAIL_DIRECTOR_PENDING_SUBSCRIPTION_EMAIL)
