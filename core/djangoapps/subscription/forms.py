from django import forms
from django.shortcuts import get_object_or_404

from common.djangolibs.utils import import_from_settings
from core.djangoapps.project.models import Project
from core.djangoapps.resources.models import Resource, ResourceType
from core.djangoapps.subscription.models import (Subscription,
                                                 SubscriptionStatusChoice)
from core.djangoapps.subscription.utils import get_user_resources


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
            status__name__in=['Active', 'Pending Add'])
        user_query_set = user_query_set.exclude(user=project_obj.pi)
        if user_query_set:
            self.fields['users'].choices = ((user.user.username, "%s %s (%s)" % (
                user.user.first_name, user.user.last_name, user.user.username)) for user in user_query_set)
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
        queryset=Resource.objects.filter(is_subscribable=True).order_by('name'),
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
    show_all_subscriptions = forms.BooleanField(initial=False, required=False)


class SubscriptionReviewUserForm(forms.Form):
    SUBSCRIPTION_REVIEW_USER_CHOICES = (
        ('keep_in_subscription_and_project', 'Keep in subscription and project'),
        ('keep_in_project_only', 'Keep in project only'),
        ('remove_from_project', 'Remove from project'),
    )

    username = forms.CharField(max_length=150, disabled=True)
    first_name = forms.CharField(max_length=30, required=False, disabled=True)
    last_name = forms.CharField(max_length=150, required=False, disabled=True)
    email = forms.EmailField(max_length=100, required=False, disabled=True)
    user_status = forms.ChoiceField(choices=SUBSCRIPTION_REVIEW_USER_CHOICES)
