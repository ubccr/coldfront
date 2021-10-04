from django import forms
from django.shortcuts import get_object_or_404

from coldfront.core.allocation.models import (Allocation, AllocationAccount,
                                              AllocationAttributeType,
                                              AllocationStatusChoice)
from coldfront.core.allocation.utils import get_user_resources
from coldfront.core.project.models import Project
from coldfront.core.resource.models import Resource, ResourceType
from coldfront.core.utils.common import import_from_settings

ALLOCATION_ACCOUNT_ENABLED = import_from_settings(
    'ALLOCATION_ACCOUNT_ENABLED', False)


class AllocationForm(forms.Form):
    resource = forms.ModelChoiceField(queryset=None, empty_label=None)
    justification = forms.CharField(widget=forms.Textarea)
    quantity = forms.IntegerField(required=True)
    users = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple, required=False)
    allocation_account = forms.ChoiceField(required=False)

    def __init__(self, request_user, project_pk,  *args, **kwargs):
        super().__init__(*args, **kwargs)
        project_obj = get_object_or_404(Project, pk=project_pk)
        self.fields['resource'].queryset = get_user_resources(request_user)
        self.fields['quantity'].initial = 1
        user_query_set = project_obj.projectuser_set.select_related('user').filter(
            status__name__in=['Active', ])
        user_query_set = user_query_set.exclude(user=project_obj.pi)
        if user_query_set:
            self.fields['users'].choices = ((user.user.username, "%s %s (%s)" % (
                user.user.first_name, user.user.last_name, user.user.username)) for user in user_query_set)
            self.fields['users'].help_text = '<br/>Select users in your project to add to this allocation.'
        else:
            self.fields['users'].widget = forms.HiddenInput()

        if ALLOCATION_ACCOUNT_ENABLED:
            allocation_accounts = AllocationAccount.objects.filter(
                user=request_user)
            if allocation_accounts:
                self.fields['allocation_account'].choices = (((account.name, account.name))
                                                             for account in allocation_accounts)

            self.fields['allocation_account'].help_text = '<br/>Select account name to associate with resource. <a href="#Modal" id="modal_link">Click here to create an account name!</a>'
        else:
            self.fields['allocation_account'].widget = forms.HiddenInput()

        self.fields['justification'].help_text = '<br/>Justification for requesting this allocation.'


class AllocationUpdateForm(forms.Form):
    status = forms.ModelChoiceField(
        queryset=AllocationStatusChoice.objects.all().order_by('name'), empty_label=None)
    start_date = forms.DateField(
        label='Start Date',
        widget=forms.DateInput(attrs={'class': 'datepicker'}),
        required=False)
    end_date = forms.DateField(
        label='End Date',
        widget=forms.DateInput(attrs={'class': 'datepicker'}),
        required=False)
    description = forms.CharField(max_length=512,
                                  label='Description',
                                  required=False)

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if start_date and end_date < start_date:
            raise forms.ValidationError(
                'End date cannot be less than start date'
            )


class AllocationInvoiceUpdateForm(forms.Form):
    status = forms.ModelChoiceField(queryset=AllocationStatusChoice.objects.filter(name__in=[
        'Payment Pending', 'Payment Requested', 'Payment Declined', 'Paid']).order_by('name'), empty_label=None)


class AllocationAddUserForm(forms.Form):
    username = forms.CharField(max_length=150, disabled=True)
    first_name = forms.CharField(max_length=30, required=False, disabled=True)
    last_name = forms.CharField(max_length=150, required=False, disabled=True)
    email = forms.EmailField(max_length=100, required=False, disabled=True)
    selected = forms.BooleanField(initial=False, required=False)


class AllocationRemoveUserForm(forms.Form):
    username = forms.CharField(max_length=150, disabled=True)
    first_name = forms.CharField(max_length=30, required=False, disabled=True)
    last_name = forms.CharField(max_length=150, required=False, disabled=True)
    email = forms.EmailField(max_length=100, required=False, disabled=True)
    selected = forms.BooleanField(initial=False, required=False)


class AllocationAttributeDeleteForm(forms.Form):
    pk = forms.IntegerField(required=False, disabled=True)
    name = forms.CharField(max_length=150, required=False, disabled=True)
    value = forms.CharField(max_length=150, required=False, disabled=True)
    selected = forms.BooleanField(initial=False, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['pk'].widget = forms.HiddenInput()


class AllocationSearchForm(forms.Form):
    project = forms.CharField(label='Project Title',
                              max_length=100, required=False)
    username = forms.CharField(
        label='Username', max_length=100, required=False)
    resource_type = forms.ModelChoiceField(
        label='Resource Type',
        queryset=ResourceType.objects.all().order_by('name'),
        required=False)
    resource_name = forms.ModelMultipleChoiceField(
        label='Resource Name',
        queryset=Resource.objects.filter(
            is_allocatable=True).order_by('name'),
        required=False)
    allocation_attribute_name = forms.ModelChoiceField(
        label='Allocation Attribute Name',
        queryset=AllocationAttributeType.objects.all().order_by('name'),
        required=False)
    allocation_attribute_value = forms.CharField(
        label='Allocation Attribute Value', max_length=100, required=False)
    end_date = forms.DateField(
        label='End Date',
        widget=forms.DateInput(attrs={'class': 'datepicker'}),
        required=False)
    active_from_now_until_date = forms.DateField(
        label='Active from Now Until Date',
        widget=forms.DateInput(attrs={'class': 'datepicker'}),
        required=False)
    status = forms.ModelMultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        queryset=AllocationStatusChoice.objects.all().order_by('name'),
        required=False)
    show_all_allocations = forms.BooleanField(initial=False, required=False)


class AllocationReviewUserForm(forms.Form):
    ALLOCATION_REVIEW_USER_CHOICES = (
        ('keep_in_allocation_and_project', 'Keep in allocation and project'),
        ('keep_in_project_only', 'Remove from this allocation only'),
        ('remove_from_project', 'Remove from project'),
    )

    username = forms.CharField(max_length=150, disabled=True)
    first_name = forms.CharField(max_length=30, required=False, disabled=True)
    last_name = forms.CharField(max_length=150, required=False, disabled=True)
    email = forms.EmailField(max_length=100, required=False, disabled=True)
    user_status = forms.ChoiceField(choices=ALLOCATION_REVIEW_USER_CHOICES)


class AllocationInvoiceNoteDeleteForm(forms.Form):
    pk = forms.IntegerField(required=False, disabled=True)
    note = forms.CharField(widget=forms.Textarea, disabled=True)
    author = forms.CharField(
        max_length=512, required=False, disabled=True)
    selected = forms.BooleanField(initial=False, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['pk'].widget = forms.HiddenInput()


class AllocationAccountForm(forms.ModelForm):

    class Meta:
        model = AllocationAccount
        fields = ['name', ]
