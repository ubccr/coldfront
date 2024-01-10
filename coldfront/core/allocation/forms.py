import logging
from datetime import date
from coldfront.core.user.models import UserProfile
from django import forms
from django.core.exceptions import ValidationError
from django.forms.widgets import RadioSelect
from django.shortcuts import get_object_or_404
from django.conf import settings

from coldfront.core.allocation.models import (AllocationAccount,
                                              AllocationAttributeType,
                                              AllocationAttribute,
                                              AllocationStatusChoice,
                                              AllocationUserRoleChoice)
from coldfront.core.allocation.utils import get_user_resources
from coldfront.core.project.models import Project
from coldfront.core.resource.models import Resource, ResourceType
from coldfront.core.utils.common import import_from_settings

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Layout, Submit, HTML, Row, Column, Fieldset, Reset
from crispy_forms.bootstrap import InlineRadios, FormActions, PrependedText

logger = logging.getLogger(__name__)

ALLOCATION_ACCOUNT_ENABLED = import_from_settings(
    'ALLOCATION_ACCOUNT_ENABLED', False)
ALLOCATION_CHANGE_REQUEST_EXTENSION_DAYS = import_from_settings(
    'ALLOCATION_CHANGE_REQUEST_EXTENSION_DAYS', [])


class AllocationForm(forms.Form):
    YES_NO_CHOICES = (
        ('Yes', 'Yes'),
        ('No', 'No')
    )
    # Leave an empty value as a choice so the form picks it as the value to check if the user has
    # already picked a choice (relevent if the form errors after submission due to missing required
    # values, prevents what the user chose from being reset. We want to check against an empty
    # string).
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
    TRAINING_INFERENCE_CHOICES = (
        ('', ''),
        ('Training', 'Training'),
        ('Inference', 'Inference'),
        ('Both', 'Both')
    )
    GRAND_CHALLENGE_CHOICES = (
        ('', ''),
        ('healthinitiative', 'Precision Health Initiative'),
        ('envchange', 'Prepared for Environmental Change'),
        ('addiction', 'Responding to the Addiction Crisis')
    )
    STORAGE_UNIT_CHOICES = (
        ('GB', 'GB'),
        ('TB', 'TB')
    )
    SYSTEM_CHOICES = (
        ('Carbonate', 'Carbonate'),
        ('BigRed3', 'Big Red 3')
    )
    ACCESS_LEVEL_CHOICES = (
        ('Masked', 'Masked'),
        ('Unmasked', 'Unmasked')
    )
    LICENSE_TERM_CHOICES = (
        ('current', 'Current license'),
        ('current_and_next_year', 'Current license + next annual license')
    )
    USE_TYPE_CHOICES = (
        ('Research', 'Research'),
        ('Class', 'Class')
    )

    resource = forms.ChoiceField(choices=())
    justification = forms.CharField(widget=forms.Textarea)
    first_name = forms.CharField(max_length=40, required=False)
    last_name = forms.CharField(max_length=40, required=False)
    campus_affiliation = forms.ChoiceField(choices=CAMPUS_CHOICES, required=False)
    email = forms.EmailField(max_length=40, required=False)
    url = forms.CharField(max_length=50, required=False)
    project_directory_name = forms.CharField(max_length=10, required=False)
    quantity = forms.IntegerField(required=False)
    storage_space = forms.IntegerField(required=False)
    storage_space_unit = forms.ChoiceField(choices=STORAGE_UNIT_CHOICES, required=False, widget=RadioSelect)
    leverage_multiple_gpus = forms.ChoiceField(choices=YES_NO_CHOICES, required=False, widget=RadioSelect)
    dl_workflow = forms.ChoiceField(choices=YES_NO_CHOICES, required=False, widget=RadioSelect)
    gpu_workflow = forms.ChoiceField(choices=YES_NO_CHOICES, required=False, widget=RadioSelect)
    applications_list = forms.CharField(max_length=128, required=False)
    training_or_inference = forms.ChoiceField(choices=TRAINING_INFERENCE_CHOICES, required=False)
    for_coursework = forms.ChoiceField(choices=YES_NO_CHOICES, required=False, widget=RadioSelect)
    system = forms.ChoiceField(choices=SYSTEM_CHOICES, required=False, widget=RadioSelect)
    is_grand_challenge = forms.BooleanField(required=False)
    grand_challenge_program = forms.ChoiceField(choices=GRAND_CHALLENGE_CHOICES, required=False)
    start_date = forms.DateField(widget=forms.TextInput(attrs={'class': 'datepicker'}), required=False)
    end_date = forms.DateField(widget=forms.TextInput(attrs={'class': 'datepicker'}), required=False)
    use_indefinitely = forms.BooleanField(required=False)
    phi_association = forms.ChoiceField(choices=YES_NO_CHOICES, required=False, widget=RadioSelect)
    access_level = forms.ChoiceField(choices=ACCESS_LEVEL_CHOICES, required=False, widget=RadioSelect)
    primary_contact = forms.CharField(max_length=20, required=False)
    secondary_contact = forms.CharField(max_length=20, required=False)
    department_full_name = forms.CharField(max_length=30, required=False)
    department_short_name = forms.CharField(max_length=15, required=False)
    fiscal_officer = forms.CharField(max_length=20, required=False)
    account_number = forms.CharField(max_length=9, required=False)
    sub_account_number = forms.CharField(max_length=20, required=False)
    license_term = forms.ChoiceField(choices=LICENSE_TERM_CHOICES, required=False)
    faculty_email = forms.EmailField(max_length=40, required=False)
    store_ephi = forms.ChoiceField(choices=YES_NO_CHOICES, required=False, widget=RadioSelect)
    it_pros = forms.CharField(max_length=100, required=False)
    devices_ip_addresses = forms.CharField(max_length=128, required=False)
    data_management_plan = forms.CharField(widget=forms.Textarea, required=False)
    prorated_cost = forms.IntegerField(disabled=True, required=False)
    cost = forms.IntegerField(disabled=True, required=False)
    total_cost = forms.IntegerField(disabled=True, required=False)
    confirm_understanding = forms.BooleanField(required=False)
    confirm_best_practices = forms.BooleanField(required=False)
    data_manager = forms.CharField(max_length=50, required=False)
    phone_number = forms.CharField(max_length=13, required=False)
    group_account_name = forms.CharField(max_length=20, required=False)
    group_account_name_exists = forms.BooleanField(required=False)
    terms_of_service = forms.BooleanField(required=False)
    data_management_responsibilities = forms.BooleanField(required=False)
    admin_ads_group = forms.CharField(max_length=64, required=False)
    user_ads_group = forms.CharField(max_length=64, required=False)
    use_type = forms.ChoiceField(choices=USE_TYPE_CHOICES, required=False, widget=RadioSelect)
    will_exceed_limit = forms.ChoiceField(choices=YES_NO_CHOICES, required=False, widget=RadioSelect)

    users = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple, required=False)
    allocation_account = forms.ChoiceField(required=False)

    def __init__(self, request_user, project_pk, after_project_creation=False, *args, **kwargs):
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
        self.fields['justification'].initial = 'No additional information needed at this time.'
        self.fields['project_directory_name'].help_text = 'Must be alphanumeric and not exceed 10 characters in length'
        self.fields['data_manager'].help_text = 'Must be a project Manager. Only this user can add and remove users from this resource. They will automatically be added to the resource.'
        self.fields['group_account_name_exists'].help_text = 'Does this IU group username already exist?'
        self.fields['group_account_name'].help_text = 'e.g. Enter IU group account username'
        self.fields['admin_ads_group'].help_text = 'This ADS group will be used to identify user(s) who will have the \
            storage allocation "admin" role. This role can create directories at the allocation top-level directory and assign \
            permissions. Geode-Project allocations are a closed-first model. Users in the "admin" role will need to create a \
            directory and assign permissions to users and groups in the "user" role ADS group (below). This must be an ADS group\
            you or your IT Pro creates/maintains.'
        self.fields['user_ads_group'].help_text = 'This ADS group will be used to identify user(s)/group(s) who will have \
            the storage allocation "user" role. This role will not be able to create directories at the allocation top-level \
            directory nor assign permissions. Geode-Project allocations are a closed-first model. Users in the "admin" role \
            will need to create a directory and assign permissions to users and groups in this "user" role ADS group. The \
            type of access a "user" role has depends upon what permissions an "admin" grants. This must be an ADS group you \
            or your IT Pro creates/maintains.'

        user_profile = UserProfile.objects.get(user=request_user)
        self.fields['department_full_name'].initial = user_profile.department
        self.fields['first_name'].initial = user_profile.user.first_name
        self.fields['last_name'].initial = user_profile.user.last_name

        if 'coldfront.plugins.ldap_user_info' in settings.INSTALLED_APPS:
            from coldfront.plugins.ldap_user_info.utils import get_user_info
            attributes = get_user_info(request_user.username, ['division', 'ou', 'mail'])
            if attributes.get('division'):
                self.fields['department_short_name'].initial = attributes['division'][0]
            if attributes.get('ou'):
                self.fields['campus_affiliation'].initial = attributes['ou'][0]
            if attributes.get('mail'):
                self.fields['email'].initial = attributes['mail'][0]

        if after_project_creation:
            form_actions = FormActions(
                Submit('submit', 'Submit and Continue'),
            )
        else:
            form_actions = FormActions(
                Submit('submit', 'Submit'),
                HTML("""<a class="btn btn-secondary" href="{% url 'project-detail' project.pk %}"
                    role="button">Back to Project</a><br>"""),
            )

        self.helper = FormHelper()
        self.helper.layout = Layout(
            'resource',
            'justification',
            'first_name',
            'last_name',
            'email',
            'phone_number',
            'url',
            'primary_contact',
            'secondary_contact',
            'it_pros',
            'department_full_name',
            'department_short_name',
            'campus_affiliation',
            'quantity',
            'storage_space',
            InlineRadios('storage_space_unit'),
            InlineRadios('use_type'),
            InlineRadios('will_exceed_limit'),
            'group_account_name',
            'group_account_name_exists',
            Field('start_date', placeholder='mm/dd/yyyy'),
            Field('end_date', placeholder='mm/dd/yyyy'),
            'use_indefinitely',
            'project_directory_name',
            'data_management_plan',
            'admin_ads_group',
            'user_ads_group',
            'fiscal_officer',
            Field('account_number', placeholder='00-000-00'),
            'sub_account_number',
            'license_term',
            PrependedText('prorated_cost', '$'),
            PrependedText('cost', '$'),
            PrependedText('total_cost', '$'),
            'data_manager',
            InlineRadios('leverage_multiple_gpus'),
            InlineRadios('gpu_workflow'),
            InlineRadios('dl_workflow'),
            Field('applications_list', placeholder='tensorflow,pytorch,etc'),
            'training_or_inference',
            InlineRadios('for_coursework'),
            InlineRadios('system'),
            'is_grand_challenge',
            'grand_challenge_program',
            InlineRadios('phi_association'),
            InlineRadios('access_level'),
            'faculty_email',
            InlineRadios('store_ephi'),
            'devices_ip_addresses',
            'confirm_understanding',
            'confirm_best_practices',
            'terms_of_service',
            'data_management_responsibilities',
            'users',
            'allocation_account',
            form_actions,
        )

    def clean(self):
        cleaned_data = super().clean()
        resource_obj = Resource.objects.get(pk=cleaned_data.get('resource'))

        resource_attribute_objs = resource_obj.resourceattribute_set.all()

        ldap_user_info_enabled = False
        if 'coldfront.plugins.ldap_user_info' in settings.INSTALLED_APPS:
            from coldfront.plugins.ldap_user_info.utils import check_if_user_exists
            ldap_user_info_enabled = True

        errors = {}
        for resource_attribute_obj in resource_attribute_objs:
            name = resource_attribute_obj.resource_attribute_type.name
            field_value = cleaned_data.get(name)
            if resource_attribute_obj.is_required:
                if not field_value:
                    if name == 'end_date':
                        use_indefinitely = resource_attribute_objs.filter(
                            resource_attribute_type__name='use_indefinitely'
                        )
                        if use_indefinitely.exists() and cleaned_data.get('use_indefinitely'):
                            continue

                    errors[name] = 'This field is required'
                    continue
            if resource_attribute_obj.check_if_username_exists:
                if field_value and ldap_user_info_enabled:
                    if ',' in field_value:
                        invalid_users = []
                        field_values = field_value.split(',')
                        for value in field_values:
                            value = value.strip()
                            if value and not check_if_user_exists(value):
                                invalid_users.append(value)

                        if invalid_users:
                            errors[name] = f'Usernames {", ".join(invalid_users)} are not valid'
                            continue
                    else:
                        if not check_if_user_exists(field_value):
                            errors[name] = 'This username is not valid'
                            continue
            if resource_attribute_obj.resource_account_is_required:
                if not resource_obj.check_user_account_exists(field_value):
                    errors[name] = 'This user does not have an account on this resource'
                    continue

            if name == 'account_number' and field_value:
                if not len(field_value) == 9:
                    errors[name] = 'Account number must have a format of ##-###-##'
                    continue
                elif not field_value[2] == '-' or not field_value[6] == '-':
                    errors[name] = 'Account number must have a format of ##-###-##'
                    continue
            elif name == 'start_date' and field_value:
                if field_value <= date.today():
                    errors[name] = 'Please select a start date later than today'
                    continue
                end_date = cleaned_data.get('end_date')
                use_indefinitely = resource_attribute_objs.filter(
                    resource_attribute_type__name='use_indefinitely'
                )
                if not use_indefinitely.exists() or not cleaned_data.get(use_indefinitely):
                    if end_date and field_value >= end_date:
                        errors[name] = 'Start date must be earlier than end date'
                        continue
            elif name == 'end_date' and field_value:
                if field_value <= date.today():
                    errors[name] = 'Please select an end date later than today'
                    continue
            elif name == 'storage_space':
                if field_value <= 0:
                    errors[name] = 'Storage space must be greater than 0'
                    continue
            elif name == 'project_directory_name':
                if not field_value.isalnum():
                    errors[name] = 'Project directory name must be alphanumeric'
                    continue

        if errors:
            for name, error in errors.items():
                try:
                    self.add_error(name, error)
                except ValueError:
                    logger.warning(f'{name} is not an internal allocation attribute and cannot have constraints. Skipping')
            raise ValidationError('Please correct the errors below')


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
    is_locked = forms.BooleanField(required=False)
    is_changeable = forms.BooleanField(required=False)

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
    role = forms.ModelChoiceField(
        queryset=AllocationUserRoleChoice.objects.none(), required=False, disabled=True)
    selected = forms.BooleanField(initial=False, required=False)

    def __init__(self, *args, **kwargs):
        resource = kwargs.pop('resource', None)
        super().__init__(*args, **kwargs)
        if resource and resource.requires_user_roles:
            self.fields['role'].disabled = False
            self.fields['role'].queryset = AllocationUserRoleChoice.objects.filter(resources=resource)

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('selected'):
            if not self.fields['role'].disabled and not cleaned_data.get('role'):
                raise ValidationError('This resource requires user roles')

        return cleaned_data


class AllocationRemoveUserForm(forms.Form):
    username = forms.CharField(max_length=150, disabled=True)
    first_name = forms.CharField(max_length=30, required=False, disabled=True)
    last_name = forms.CharField(max_length=150, required=False, disabled=True)
    email = forms.EmailField(max_length=100, required=False, disabled=True)
    selected = forms.BooleanField(initial=False, required=False)

    def __init__(self, *args, disable_selected, **kwargs):
        super().__init__(*args, **kwargs)
        if disable_selected:
            self.fields['selected'].disabled = True


class AllocationRemoveUserFormset(forms.BaseFormSet):
    def get_form_kwargs(self, index):
        """
        Override so specific users can be prevented from being removed.
        """
        kwargs = super().get_form_kwargs(index)
        disable_selected = kwargs['disable_selected'][index]
        return {'disable_selected': disable_selected}

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


class AllocationInvoiceSearchForm(forms.Form):
    resource_type = forms.ModelChoiceField(
        label='Resource Type',
        queryset=ResourceType.objects.all().order_by('name'),
        required=False
    )
    resource_name = forms.ModelMultipleChoiceField(
        label='Resource Name',
        queryset=Resource.objects.filter(is_allocatable=True).order_by('name'),
        required=False
    )
    start_date = forms.DateField(
        label='Start Date',
        widget=forms.DateInput(attrs={'class': 'datepicker'}),
        required=False
    )
    end_date = forms.DateField(
        label='End Date',
        widget=forms.DateInput(attrs={'class': 'datepicker'}),
        required=False
    )


class AllocationInvoiceExportForm(forms.Form):
    file_name = forms.CharField(max_length=64, initial='invoices')
    resource = forms.ChoiceField(choices=())
    allocation_status = forms.ModelMultipleChoiceField(
        label='Allocation status',
        queryset=AllocationStatusChoice.objects.filter(name__in=['Active', 'Billing Information Submitted', ]).order_by('name')
    )
    # start_date = forms.DateField(
    #     widget=forms.DateInput(attrs={'class': 'datepicker'}),
    #     required=False
    # )
    # end_date = forms.DateField(
    #     widget=forms.DateInput(attrs={'class': 'datepicker'}),
    #     required=False
    # )

    def __init__(self, *args, resources=None, **kwargs):
        super().__init__(*args, **kwargs)

        if resources is None:
            self.fields['resource'].choices = ()
        else:
            self.fields['resource'].choices = resources


class AllocationReviewUserForm(forms.Form):
    # No relation to AllocationUserReview model.
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


class AllocationAttributeChangeForm(forms.Form):
    pk = forms.IntegerField(required=False, disabled=True)
    name = forms.CharField(max_length=150, required=False, disabled=True)
    value = forms.CharField(max_length=150, required=False, disabled=True)
    new_value = forms.CharField(max_length=150, required=False, disabled=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['pk'].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data.get('new_value') != "":
            allocation_attribute = AllocationAttribute.objects.get(pk=cleaned_data.get('pk'))
            allocation_attribute.value = cleaned_data.get('new_value')
            allocation_attribute.clean()


class AllocationAttributeUpdateForm(forms.Form):
    change_pk = forms.IntegerField(required=False, disabled=True)
    attribute_pk = forms.IntegerField(required=False, disabled=True)
    name = forms.CharField(max_length=150, required=False, disabled=True)
    value = forms.CharField(max_length=150, required=False, disabled=True)
    new_value = forms.CharField(max_length=150, required=False, disabled=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['change_pk'].widget = forms.HiddenInput()
        self.fields['attribute_pk'].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()
        allocation_attribute = AllocationAttribute.objects.get(pk=cleaned_data.get('attribute_pk'))

        allocation_attribute.value = cleaned_data.get('new_value')
        allocation_attribute.clean()


class AllocationAttributeEditForm(forms.Form):
    attribute_pk = forms.IntegerField(required=False, disabled=True)
    name = forms.CharField(max_length=150, required=False, disabled=True)
    value = forms.CharField(max_length=150, required=False, disabled=True)
    new_value = forms.CharField(max_length=150, required=False, disabled=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['attribute_pk'].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('new_value'):
            allocation_attribute = AllocationAttribute.objects.get(pk=cleaned_data.get('attribute_pk'))
            allocation_attribute.value = cleaned_data.get('new_value')
            allocation_attribute.clean()


class AllocationChangeForm(forms.Form):
    EXTENSION_CHOICES = [
        (0, "No Extension")
    ]
    for choice in ALLOCATION_CHANGE_REQUEST_EXTENSION_DAYS:
        EXTENSION_CHOICES.append((choice, "{} days".format(choice)))

    end_date_extension = forms.TypedChoiceField(
        label='Request End Date Extension',
        choices = EXTENSION_CHOICES,
        coerce=int,
        required=False,
        empty_value=0,)
    justification = forms.CharField(
        label='Justification for Changes',
        widget=forms.Textarea,
        required=True,
        help_text='Justification for requesting this allocation change request.')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class AllocationChangeNoteForm(forms.Form):
        notes = forms.CharField(
            max_length=512, 
            label='Notes', 
            required=False, 
            widget=forms.Textarea,
            help_text="Leave any feedback about the allocation change request.")


class AllocationExportForm(forms.Form):
    file_name = forms.CharField(max_length=64, initial='allocations')
    allocation_statuses = forms.ModelMultipleChoiceField(
        queryset=AllocationStatusChoice.objects.all().order_by('name'),
        help_text='Do not select any if you want all statuses',
        required=False
    )
    allocation_resources = forms.ModelMultipleChoiceField(
        queryset=Resource.objects.all().order_by('name'),
        help_text='Do not select any if you want all resources',
        required=False
    )
    allocation_creation_range_start = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'datepicker'}),
        label='Start',
        help_text='Includes start date',
        required=False
    )
    allocation_creation_range_stop = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'datepicker'}),
        label='Stop',
        help_text='Does not include end date',
        required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            'file_name',
            Row(
                Column('allocation_statuses', css_class='col-md-6'),
                Column('allocation_resources', css_class='col-md-6'),
            ),
            Fieldset(
                'Allocation Creation Range',
                Row(
                    Column('allocation_creation_range_start', css_class='col-md-6'),
                    Column('allocation_creation_range_stop', css_class='col-md-6'),
                )
            ),
            Submit('submit', 'Export', css_class='btn-success'),
            Reset('reset', 'Reset', css_class='btn-secondary')
        )


class AllocationUserUpdateForm(forms.Form):
    role = forms.ModelChoiceField(
        queryset=AllocationUserRoleChoice.objects.none(), required=False, disabled=True)
    enable_notifications = forms.BooleanField(initial=False, required=False)

    def __init__(self, *args, **kwargs):
        disable_enable_notifications = kwargs.pop('disable_enable_notifications', False)
        resource = kwargs.pop('resource', None)
        super().__init__(*args, **kwargs)
        if resource and resource.requires_user_roles:
            self.fields['role'].disabled = False
            self.fields['role'].queryset = AllocationUserRoleChoice.objects.filter(resources=resource)

        if disable_enable_notifications:
            self.fields['enable_notifications'].disabled = True

    def clean(self):
        cleaned_data = super().clean()
        if not self.fields['role'].disabled and not cleaned_data.get('role'):
            raise ValidationError('This resource requires user roles')

        return cleaned_data