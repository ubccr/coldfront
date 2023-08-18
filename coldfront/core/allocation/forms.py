import re

from django import forms
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404

from coldfront.core.allocation.models import (
    AllocationAccount,
    AllocationAttributeType,
    AllocationAttribute,
    AllocationStatusChoice
)
from coldfront.core.allocation.utils import get_user_resources
from coldfront.core.project.models import Project
from coldfront.core.resource.models import Resource, ResourceType
from coldfront.core.utils.common import import_from_settings

ALLOCATION_ACCOUNT_ENABLED = import_from_settings(
    'ALLOCATION_ACCOUNT_ENABLED', False)
ALLOCATION_CHANGE_REQUEST_EXTENSION_DAYS = import_from_settings(
    'ALLOCATION_CHANGE_REQUEST_EXTENSION_DAYS', [])
HSPH_CODE = import_from_settings('HSPH_CODE', '000-000-000-000-000-000-000-000-000-000-000')
SEAS_CODE = import_from_settings('SEAS_CODE', '111-111-111-111-111-111-111-111-111-111-111')

class ExpenseCodeField(forms.CharField):
    """custom field for expense_code"""

    # def validate(self, value):
    #     if value:
    #         digits_only = re.sub(r'\D', '', value)
    #         if not re.fullmatch(r'^(\d+-?)*[\d-]+$', value):
    #             raise ValidationError("Input must consist only of digits and dashes.")
    #         if len(digits_only) != 33:
    #             raise ValidationError("Input must contain exactly 33 digits.")

    def clean(self, value):
        # Remove all dashes from the input string to count the number of digits
        value = super().clean(value)
        digits_only = re.sub(r'[^0-9xX]', '', value)
        insert_dashes = lambda d: '-'.join(
            [d[:3], d[3:8], d[8:12], d[12:18], d[18:24], d[24:28], d[28:33]]
        )
        formatted_value = insert_dashes(digits_only)
        return formatted_value


class AllocationForm(forms.Form):
    DEFAULT_DESCRIPTION = """
We do not have information about your research. Please provide a detailed description of your work and update your field of science. Thank you!
        """
    # resource = forms.ModelChoiceField(queryset=None, empty_label=None)
    quantity = forms.IntegerField(required=True, initial=1)

    expense_code = ExpenseCodeField(
        label="Lab's 33 digit expense code", required=False
    )

    hsph_code = forms.BooleanField(
        label='The PI is part of HSPH and storage should be billed to their code',
        required=False
    )

    seas_code = forms.BooleanField(
        label='The PI is part of SEAS and storage should be billed to their code',
        required=False
    )

    tier = forms.ModelChoiceField(
        queryset=Resource.objects.filter(resource_type__name='Storage Tier'),
        label='Resource Tier'
    )
    heavy_io = forms.BooleanField(
        label='My lab will perform heavy I/O from the cluster against this space (more than 100 cores)',
        required=False
    )
    mounted = forms.BooleanField(
        label='My lab intends to mount the storage to our local machine as an additional drive',
        required=False
    )
    external_sharing = forms.BooleanField(
        label='My lab intends to share some of this data with collaborators outside of Harvard',
        required=False
    )
    high_security = forms.BooleanField(
        label='This allocation will store secure information (security level three or greater)',
        required=False
    )
    dua = forms.BooleanField(
        label="Some or all of my lab’s data is governed by DUAs", required=False
    )
    justification = forms.CharField(
        widget=forms.Textarea,
        help_text = '<br/>Justification for requesting this allocation. Please provide details here about the usecase or datacenter choices (what data needs to be accessed, expectation of frequent transfer to or from Campus, need for Samba connectivity, etc.)'
    )

    #users = forms.MultipleChoiceField(
    #    widget=forms.CheckboxSelectMultiple, required=False)


    def __init__(self, request_user, project_pk,  *args, **kwargs):
        super().__init__(*args, **kwargs)
        project_obj = get_object_or_404(Project, pk=project_pk)
        self.fields['tier'].queryset = get_user_resources(request_user).filter(
            resource_type__name='Storage Tier'
        ).order_by(Lower("name"))
        user_query_set = project_obj.projectuser_set.select_related('user').filter(
            status__name__in=['Active', ]).order_by("user__username")
        user_query_set = user_query_set.exclude(user=project_obj.pi)
        # if user_query_set:
        #     self.fields['users'].choices = ((user.user.username, "%s %s (%s)" % (
        #         user.user.first_name, user.user.last_name, user.user.username)) for user in user_query_set)
        #     self.fields['users'].help_text = '<br/>Select users in your project to add to this allocation.'
        # else:
        #     self.fields['users'].widget = forms.HiddenInput()


    def clean(self):
        cleaned_data = super().clean()
        # Remove all dashes from the input string to count the number of digits
        value = cleaned_data.get("expense_code")
        hsph_val = cleaned_data.get("hsph_code")
        seas_val = cleaned_data.get("seas_code")
        trues = sum(x for x in [(value not in ['', '------']), hsph_val, seas_val])

        if trues != 1:
            self.add_error("expense_code", "you must select exactly one from hsph, seas, or manual entry")

        elif value and value != '------':
            digits_only = re.sub(r'[^0-9xX]', '', value)
            if not re.fullmatch(r'^([0-9xX]+-?)*[0-9xX-]+$', value):
                self.add_error("expense_code", "Input must consist only of digits and dashes.")
            elif len(digits_only) != 33:
                self.add_error("expense_code", "Input must contain exactly 33 digits.")
            else:
                insert_dashes = lambda d: '-'.join(
                    [d[:3], d[3:8], d[8:12], d[12:18], d[18:24], d[24:28], d[28:33]]
                )
                cleaned_data['expense_code'] = insert_dashes(digits_only)
        elif hsph_val:
            cleaned_data['expense_code'] = HSPH_CODE
        elif seas_val:
            cleaned_data['expense_code'] = SEAS_CODE
        return cleaned_data


class AllocationResourceChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        label_str = f'{obj.name}'
        if obj.used_percentage != None:
            label_str += f' ({obj.used_percentage}% full)'
        return label_str


class AllocationUpdateForm(forms.Form):
    resource = forms.ModelChoiceField(
        label='Resource', queryset=Resource.objects.all(), required=False
    )
    status = forms.ModelChoiceField(
        queryset=AllocationStatusChoice.objects.all().order_by(Lower("name")), empty_label=None)
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
                    parent_resource=allo_resource
                )
            else:
                self.fields['resource'].required = False
                self.fields['resource'].queryset = Resource.objects.filter(
                    pk=allo_resource.pk
                )


    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError('End date cannot be less than start date')
        return cleaned_data


class AllocationInvoiceUpdateForm(forms.Form):
    status = forms.ModelChoiceField(queryset=AllocationStatusChoice.objects.filter(
        name__in=['Payment Pending', 'Payment Requested', 'Payment Declined', 'Paid']
    ).order_by(Lower("name")), empty_label=None)


class AllocationAddUserForm(forms.Form):
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
        queryset=ResourceType.objects.all().order_by(Lower("name")),
        required=False)
    resource_name = forms.ModelMultipleChoiceField(
        label='Resource Name',
        queryset=Resource.objects.filter(
            is_allocatable=True).order_by(Lower("name")),
        required=False)
    allocation_attribute_name = forms.ModelChoiceField(
        label='Allocation Attribute Name',
        queryset=AllocationAttributeType.objects.all().order_by(Lower("name")),
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
        queryset=AllocationStatusChoice.objects.all().order_by(Lower("name")),
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
            help_text="Leave any feedback about the allocation change request.")

class AllocationAttributeCreateForm(forms.ModelForm):
    class Meta:
        model = AllocationAttribute
        fields = '__all__'
    def __init__(self, *args, **kwargs):
        super(AllocationAttributeCreateForm, self).__init__(*args, **kwargs)
        self.fields['allocation_attribute_type'].queryset = self.fields['allocation_attribute_type'].queryset.order_by(Lower('name'))
