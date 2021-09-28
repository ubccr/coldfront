from django import forms
from django.forms.widgets import RadioSelect
from django.shortcuts import get_object_or_404
from django.utils.module_loading import import_string

from coldfront.core.allocation.models import (AllocationAccount,
                                              AllocationAttributeType,
                                              AllocationStatusChoice)
from coldfront.core.allocation.utils import get_user_resources, compute_prorated_amount
from coldfront.core.project.models import Project
from coldfront.core.resource.models import Resource, ResourceType
from coldfront.core.utils.common import import_from_settings

ALLOCATION_ACCOUNT_ENABLED = import_from_settings(
    'ALLOCATION_ACCOUNT_ENABLED', False)


class AllocationForm(forms.Form):
    resource = forms.ModelChoiceField(queryset=None, empty_label=None)
    justification = forms.CharField(widget=forms.Textarea)
    first_name = forms.CharField(max_length=40, required=False)
    last_name = forms.CharField(max_length=40, required=False)
    campus_affiliation = forms.ChoiceField(
        choices=(
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
        ),
        required=False
    )
    email = forms.CharField(max_length=40, required=False)
    url = forms.CharField(max_length=50, required=False)
    project_directory_name = forms.CharField(max_length=10, required=False)
    quantity = forms.IntegerField(required=False)
    storage_space = forms.IntegerField(required=False)
    storage_space_with_unit = forms.IntegerField(required=False)
    leverage_multiple_gpus = forms.ChoiceField(choices=(('No', 'No'), ('Yes', 'Yes')), required=False, widget=RadioSelect)
    dl_workflow = forms.ChoiceField(choices=(('No', 'No'), ('Yes', 'Yes')), required=False, widget=RadioSelect)
    applications_list = forms.CharField(max_length=150, required=False)
    # Leave an empty value as a choice so the form picks it as the value to check if the user has
    # already picked a choice (relevent if the form errors after submission due to missing required
    # values, prevents what the user chose from being reset. We want to check against an empty
    # string).
    training_or_inference = forms.ChoiceField(choices=(('', ''), ('Training', 'Training'), ('Inference', 'Inference'), ('Both', 'Both')), required=False)
    for_coursework = forms.ChoiceField(choices=(('No', 'No'), ('Yes', 'Yes')), required=False, widget=RadioSelect)
    system = forms.ChoiceField(choices=(('Carbonate', 'Carbonate'), ('BigRed3', 'Big Red 3')), required=False, widget=RadioSelect)
    is_grand_challenge = forms.BooleanField(required=False)
    grand_challenge_program = forms.ChoiceField(choices=(('', ''), ('healthinitiative', 'Precision Health Initiative'), ('envchange', 'Prepared for Environmental Change'), ('addiction', 'Responding to the Addiction Crisis')), required=False)
    start_date = forms.DateField(widget=forms.TextInput(attrs={'class':'datepicker'}), required=False)
    end_date = forms.DateField(widget=forms.TextInput(attrs={'class':'datepicker'}), required=False)
    use_indefinitely = forms.BooleanField(required=False)
    phi_association = forms.ChoiceField(choices=(('No', 'No'), ('Yes', 'Yes')), required=False, widget=RadioSelect)
    access_level = forms.ChoiceField(choices=(('Masked', 'Masked'), ('Unmasked', 'Unmasked')), required=False, widget=RadioSelect)
    unit = forms.CharField(max_length=10, required=False)
    primary_contact = forms.CharField(max_length=20, required=False)
    secondary_contact = forms.CharField(max_length=20, required=False)
    department_full_name = forms.CharField(max_length=30, required=False)
    department_short_name = forms.CharField(max_length=15, required=False)
    fiscal_officer = forms.CharField(max_length=20, required=False)
    account_number = forms.CharField(max_length=9, required=False)
    sub_account_number = forms.CharField(max_length=20, required=False)
    license_term = forms.ChoiceField(choices=(('current','Current license'), ('current_and_next_year','Current license + next annual license')), required=False)
    faculty_email = forms.CharField(max_length=40, required=False)
    store_ephi = forms.ChoiceField(
        choices=(('No', 'No'), ('Yes', 'Yes')),
        required=False,
        widget=RadioSelect
    )
    it_pros = forms.CharField(max_length=100, required=False)
    devices_ip_addresses = forms.CharField(max_length=200, required=False)
    data_management_plan = forms.CharField(widget=forms.Textarea, required=False)
    prorated_cost = forms.IntegerField(disabled=True, required=False)
    cost = forms.IntegerField(disabled=True, required=False)
    total_cost = forms.IntegerField(disabled=True, required=False)
    confirm_understanding = forms.BooleanField(required=False)

    users = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple, required=False)
    allocation_account = forms.ChoiceField(required=False)

    def __init__(self, request_user, project_pk,  *args, **kwargs):
        super().__init__(*args, **kwargs)
        project_obj = get_object_or_404(Project, pk=project_pk)
        self.fields['resource'].queryset = get_user_resources(request_user)
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
        self.fields['start_date'].help_text = 'Format: mm/dd/yyyy'
        self.fields['end_date'].help_text = 'Format: mm/dd/yyyy'
        self.fields['storage_space_with_unit'].help_text = 'Amount must be greater than or equal to 200GB.'
        self.fields['account_number'].help_text = 'Format: 00-000-00'
        self.fields['applications_list'].help_text = 'Format: app1,app2,app3,etc'
        self.fields['it_pros'].help_text = 'Format: name1,name2,name3,etc'

        ldap_search = import_string('coldfront.plugins.ldap_user_search.utils.LDAPSearch')
        search_class_obj = ldap_search()
        attributes = search_class_obj.search_a_user(
            request_user.username,
            ['department', 'division', 'ou', 'displayName', 'mail']
        )
        self.fields['department_full_name'].initial = attributes['department'][0]
        self.fields['department_short_name'].initial = attributes['division'][0]
        full_name = attributes['displayName'][0].split(', ')
        self.fields['first_name'].initial = full_name[1]
        self.fields['last_name'].initial = full_name[0]
        self.fields['campus_affiliation'].initial = attributes['ou'][0]
        self.fields['email'].initial = attributes['mail'][0]


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

        if start_date and end_date and end_date < start_date:
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
