import logging
import re

from django import forms
from django.conf import settings
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator

from coldfront.core.allocation.models import (
    AllocationAccount,
    AllocationAttributeType,
    AllocationAttribute,
    AllocationStatusChoice,
    AllocationUserAttribute,
    AllocationUser
)
from coldfront.core.allocation.utils import get_user_resources
from coldfront.core.project.models import Project
from coldfront.core.resource.models import Resource, ResourceType
from coldfront.core.utils.common import import_from_settings

if 'ifxbilling' in settings.INSTALLED_APPS:
    from fiine.client import API as FiineAPI
    from ifxbilling.models import Account, UserProductAccount

ALLOCATION_ACCOUNT_ENABLED = import_from_settings(
    'ALLOCATION_ACCOUNT_ENABLED', False)
ALLOCATION_CHANGE_REQUEST_EXTENSION_DAYS = import_from_settings(
    'ALLOCATION_CHANGE_REQUEST_EXTENSION_DAYS', [])
HSPH_CODE = import_from_settings('HSPH_CODE', '000-000-000-000-000-000-000-000-000-000-000')
SEAS_CODE = import_from_settings('SEAS_CODE', '111-111-111-111-111-111-111-111-111-111-111')

logger = logging.getLogger(__name__)


class ExpenseCodeField(forms.CharField):
    """custom field for expense_code"""

    def validate(self, value):
        digits_only = lambda v: re.sub(r'[^0-9xX]', '', v)
        if value and value != '------':
            if re.search(r'[^0-9xX\-\.]', value):
                raise ValidationError(
                    "Input must consist only of digits (or x'es) and dashes."
                )
            if len(digits_only(value)) != 33:
                raise ValidationError('Input must contain exactly 33 digits.')
            if 'x' in digits_only(value)[:8]+digits_only(value)[12:]:
                raise ValidationError(
                    'xes are only allowed in place of the product code (the third grouping of characters in the code)'
                )

    def clean(self, value):
        # Remove all dashes from the input string to count the number of digits
        value = super().clean(value)
        # digits_only = lambda v: re.sub(r'[^0-9xX]', '', v)
        # insert_dashes = lambda d: '-'.join(
        #     [d[:3], d[3:8], d[8:12], d[12:18], d[18:24], d[24:28], d[28:33]]
        # )
        # formatted_value = insert_dashes(digits_only)
        return value


class AllocationUserRawSareField(forms.CharField):
    """custom field for rawshare"""

    def validate(self, value):
        try:
            integer_value = int(value)
            if integer_value < 0:
                raise ValidationError('RawShare value must be a positive integer number or the string "parent".')
            if integer_value > 1410065399:
                raise ValidationError('RawShare value must be a positive integer number below 1410065399 or the string "parent".')
        except ValueError:
            if value not in ['parent']:
                raise ValidationError('RawShare value must be a positive integer number or the string "parent".')
        except Exception:
            raise ValidationError('Invalid RawShare value detected. It must be a positive integer number or the string "parent".')

    def clean(self, value):
        value = super().clean(value)
        return value


ALLOCATION_SPECIFICATIONS = [
    ('Heavy IO', 'My lab will perform heavy I/O from the cluster against this space (more than 100 cores)'),
    ('Mounted', 'My lab intends to mount the storage to our local machine as an additional drive'),
    ('External Sharing', 'My lab intends to share some of this data with collaborators outside of Harvard'),
    ('High Security', 'This allocation will store secure information (security level three or greater)'),
    ('DUA', "Some or all of my lab’s data is governed by DUAs"),
]

class AllocationForm(forms.Form):
    QS_CHOICES = [
        (HSPH_CODE, f'{HSPH_CODE} (PI is part of HSPH and storage should be billed to their code)'),
        (SEAS_CODE, f'{SEAS_CODE} (PI is part of SEAS and storage should be billed to their code)')
    ]
    DEFAULT_DESCRIPTION = """
We do not have information about your research. Please provide a detailed description of your work and update your field of science. Thank you!
        """
    # resource = forms.ModelChoiceField(queryset=None, empty_label=None)

    existing_expense_codes = forms.ChoiceField(
        label='Either select an existing expense code...',
        choices=QS_CHOICES,
        required=False,
    )

    expense_code = ExpenseCodeField(
        label='...or add a new 33 digit expense code manually here.', required=False
    )

    tier = forms.ModelChoiceField(
        queryset=Resource.objects.filter(resource_type__name='Storage Tier'),
        label='Resource Tier'
    )

    quantity = forms.IntegerField(required=True, initial=1)

    justification = forms.CharField(
        widget=forms.Textarea,
        help_text = '<br/>Justification for requesting this allocation. Please provide details here about the usecase or datacenter choices (what data needs to be accessed, expectation of frequent transfer to or from Campus, need for Samba connectivity, etc.)'
    )

    additional_specifications = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple,
        choices=ALLOCATION_SPECIFICATIONS,
    )
    #users = forms.MultipleChoiceField(
    #    widget=forms.CheckboxSelectMultiple, required=False)

    def __init__(self, request_user, project_pk,  *args, **kwargs):
        super().__init__(*args, **kwargs)
        project_obj = get_object_or_404(Project, pk=project_pk)
        self.fields['tier'].queryset = get_user_resources(request_user).filter(
            resource_type__name='Storage Tier'
        ).order_by(Lower('name'))
        existing_expense_codes = [(None, '------')] + [
            (a.code, f'{a.code} ({a.name})') for a in Account.objects.filter(
                userproductaccount__is_valid=1,
                userproductaccount__user=project_obj.pi
            ).distinct()
        ] + self.QS_CHOICES
        self.fields['existing_expense_codes'].choices = existing_expense_codes
        user_query_set = project_obj.projectuser_set.select_related('user').filter(
            status__name__in=['Active', ]
        ).order_by('user__username').exclude(user=project_obj.pi)
        # if user_query_set:
        #     self.fields['users'].choices = ((user.user.username, "%s %s (%s)" % (
        #         u.user.first_name, u.user.last_name, u.user.username)) for u in user_query_set)
        #     self.fields['users'].help_text = '<br/>Select users in your project to add to this allocation.'
        # else:
        #     self.fields['users'].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()
        # Remove all dashes from the input string to count the number of digits
        expense_code = cleaned_data.get('expense_code')
        existing_expense_codes = cleaned_data.get('existing_expense_codes')
        trues = sum(x for x in [
            (expense_code not in ['', '------']),
            (existing_expense_codes not in ['', '------']),
        ])
        digits_only = lambda v: re.sub(r'[^0-9xX]', '', v)
        if trues != 1:
            self.add_error(
                'existing_expense_codes',
                'You must either select an existing expense code or manually enter a new one.'
            )

        elif expense_code and expense_code != '------':
            replace_productcode = lambda s: s[:8] + '8250' + s[12:]
            insert_dashes = lambda d: '-'.join(
                [d[:3], d[3:8], d[8:12], d[12:18], d[18:24], d[24:28], d[28:33]]
            )
            cleaned_expensecode = insert_dashes(replace_productcode(digits_only(expense_code)))
            cleaned_data['expense_code'] = cleaned_expensecode
        elif existing_expense_codes and existing_expense_codes != '------':
            cleaned_data['expense_code'] = existing_expense_codes
        return cleaned_data


ALLOCATION_AUTOCREATE_OPTIONS = [
    ('1', 'I have already created the allocation.'),
    ('2', 'I would like to use the automated allocation creation process. If issues arise in the course of creation, I understand I may need to manually complete the allocation creation process.'),
]

class AllocationApprovalForm(forms.Form):

    sheetcheck = forms.BooleanField(
        label='I have ensured that enough space is available on this resource.',
        required=False,
    )
    auto_create_opts = forms.ChoiceField(
        label='How will this allocation be created?',
        required=False,
        widget=forms.RadioSelect,
        choices=ALLOCATION_AUTOCREATE_OPTIONS,
    )

    automation_specifications = forms.MultipleChoiceField(
        label='If you have opted for automatic allocation creation, please select from the following options:',
        required=False,
        widget=forms.CheckboxSelectMultiple,
        choices=(
            ('snapshots', 'Enable daily snapshots, 7 days of retention, for this allocation'),
            ('nfs_share', 'Create a NFS share for this allocation'),
            ('cifs_share', 'Create a CIFS share for this allocation'),
        ),
    )

    def clean(self):
        cleaned_data = super().clean()
        auto_create_opts = cleaned_data.get('auto_create_opts')
        automation_specifications = cleaned_data.get('automation_specifications')
        # if the action is 'approve', make auto_create_opts and sheetcheck mandatory
        if not auto_create_opts:
            self.add_error(
                'auto_create_opts',
                'You must select an option for how the allocation will be created.'
            )
        if auto_create_opts == '2':
            if not automation_specifications:
                self.add_error(
                    'automation_specifications',
                    'You must select at least one automation option if you choose to automatically create the allocation.'
                )
            if not cleaned_data.get('sheetcheck'):
                self.add_error(
                    'sheetcheck',
                    'You must confirm that you have checked the space availability on this resource.'
                )
        return cleaned_data


class AllocationResourceChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        label_str = f'{obj.name}'
        if obj.used_percentage != None:
            label_str += f' ({obj.used_percentage}% full)'
        return label_str


class AllocationUpdateForm(forms.Form):
    resource = AllocationResourceChoiceField(
        label='Resource', queryset=Resource.objects.all(), required=False
    )
    status = forms.ModelChoiceField(
        queryset=AllocationStatusChoice.objects.all().order_by(Lower('name')), empty_label=None)
    start_date = forms.DateField(
        label='Start Date',
        widget=forms.DateInput(attrs={'class': 'datepicker'}),
        required=False)
    end_date = forms.DateField(
        label='End Date',
        widget=forms.DateInput(attrs={'class': 'datepicker'}),
        required=False)
    description = forms.CharField(
        max_length=512, label='Description', required=False
    )
    is_locked = forms.BooleanField(required=False)
    is_changeable = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        allo_resource = kwargs['initial'].pop('resource')
        super().__init__(*args, **kwargs)
        if not allo_resource:
            self.fields['resource'].queryset = Resource.objects.exclude(
                resource_type__name='Storage Tier'
            )
        else:
            if allo_resource.resource_type.name == 'Storage Tier':
                self.fields['resource'].queryset = Resource.objects.filter(
                    parent_resource=allo_resource,
                    is_allocatable=True
                )
            else:
                self.fields['resource'].required = False
                self.fields['resource'].queryset = Resource.objects.filter(
                    pk=allo_resource.pk
                )

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError('End date cannot be less than start date')
        return cleaned_data


class AllocationInvoiceUpdateForm(forms.Form):
    status = forms.ModelChoiceField(queryset=AllocationStatusChoice.objects.filter(
        name__in=['Payment Pending', 'Payment Requested', 'Payment Declined', 'Paid']
    ).order_by(Lower('name')), empty_label=None)


class AllocationAddUserForm(forms.Form):
    username = forms.CharField(max_length=150, disabled=True)
    first_name = forms.CharField(max_length=150, required=False, disabled=True)
    last_name = forms.CharField(max_length=150, required=False, disabled=True)
    email = forms.EmailField(max_length=100, required=False, disabled=True)
    selected = forms.BooleanField(initial=False, required=False)

class AllocationAddNonProjectUserForm(forms.Form):
    username = forms.CharField(max_length=150, disabled=True)
    first_name = forms.CharField(max_length=150, required=False, disabled=True)
    last_name = forms.CharField(max_length=150, required=False, disabled=True)
    email = forms.EmailField(max_length=100, required=False, disabled=True)
    selected = forms.BooleanField(initial=False, required=False)


class AllocationRemoveUserForm(forms.Form):
    username = forms.CharField(max_length=150, disabled=True)
    first_name = forms.CharField(max_length=150, required=False, disabled=True)
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
    username = forms.CharField(label='Username', max_length=100, required=False)
    resource_type = forms.ModelChoiceField(
        label='Resource Type',
        queryset=ResourceType.objects.all().order_by(Lower('name')),
        required=False)
    resource_name = forms.ModelMultipleChoiceField(
        label='Resource Name',
        queryset=Resource.objects.filter(
            is_public=True).order_by(Lower('name')),
        required=False)
    allocation_attribute_name = forms.ModelChoiceField(
        label='Allocation Attribute Name',
        queryset=AllocationAttributeType.objects.all().order_by(Lower('name')),
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
        queryset=AllocationStatusChoice.objects.all().order_by(Lower('name')),
        required=False)
    show_all_allocations = forms.BooleanField(initial=False, required=False)


class AllocationReviewUserForm(forms.Form):
    ALLOCATION_REVIEW_USER_CHOICES = (
        ('keep_in_allocation_and_project', 'Keep in allocation and project'),
        ('keep_in_project_only', 'Remove from this allocation only'),
        ('remove_from_project', 'Remove from project'),
    )

    username = forms.CharField(max_length=150, disabled=True)
    first_name = forms.CharField(max_length=150, required=False, disabled=True)
    last_name = forms.CharField(max_length=150, required=False, disabled=True)
    email = forms.EmailField(max_length=100, required=False, disabled=True)
    user_status = forms.ChoiceField(choices=ALLOCATION_REVIEW_USER_CHOICES)


class AllocationInvoiceNoteDeleteForm(forms.Form):
    pk = forms.IntegerField(required=False, disabled=True)
    note = forms.CharField(widget=forms.Textarea, disabled=True)
    author = forms.CharField(max_length=512, required=False, disabled=True)
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

        if cleaned_data.get('new_value') != '':
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


class AllocationUserAttributeUpdateForm(forms.Form):
    allocationuser_pk = forms.IntegerField(required=True)
    value = AllocationUserRawSareField(required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['allocationuser_pk'].widget = forms.HiddenInput()


class AllocationChangeForm(forms.Form):
    EXTENSION_CHOICES = [
        (0, 'No Extension')
    ]
    for choice in ALLOCATION_CHANGE_REQUEST_EXTENSION_DAYS:
        EXTENSION_CHOICES.append((choice, f'{choice} days'))

    end_date_extension = forms.TypedChoiceField(
        label='Request End Date Extension',
        choices = EXTENSION_CHOICES,
        coerce=int,
        required=False,
        empty_value=0,)
    justification = forms.CharField(
        label='Justification for Changes',
        widget=forms.Textarea,
        required=False,
        help_text='Justification for requesting this allocation change request.')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class AllocationChangeNoteForm(forms.Form):
    notes = forms.CharField(
            max_length=512,
            label='Notes',
            required=False,
            widget=forms.Textarea,
            help_text='Leave any feedback about the allocation change request.')


ALLOCATION_AUTOUPDATE_OPTIONS = [
    ('1', 'I have already modified the allocation.'),
    ('2', 'I would like to use the automated allocation modification process. If any issues arise in the course of the modification process, I understand I may need to modify the allocation manually instead.'),
]

class AllocationAutoUpdateForm(forms.Form):
    sheetcheck = forms.BooleanField(
        label='I have ensured that enough space is available on this resource.',
        required=True
    )
    auto_update_opts = forms.ChoiceField(
        label='How will this allocation be modified?',
        required=True,
        widget=forms.RadioSelect,
        choices=ALLOCATION_AUTOUPDATE_OPTIONS,
    )


class AllocationAttributeCreateForm(forms.ModelForm):
    class Meta:
        model = AllocationAttribute
        fields = '__all__'
    def __init__(self, *args, **kwargs):
        super(AllocationAttributeCreateForm, self).__init__(*args, **kwargs)
        self.fields['allocation_attribute_type'].queryset = self.fields['allocation_attribute_type'].queryset.order_by(Lower('name'))
