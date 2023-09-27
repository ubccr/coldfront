from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.core.validators import MinLengthValidator
from django.core.validators import RegexValidator

from coldfront.core.billing.models import BillingActivity
from coldfront.core.billing.utils.queries import get_billing_activity_from_full_id
from coldfront.core.billing.utils.validation import is_billing_id_valid
from coldfront.core.project.models import Project


# TODO: Replace this module with a directory as needed.


class BillingActivityChoiceField(forms.ModelChoiceField):

    @staticmethod
    def label_from_instance(obj):
        return obj.full_id()


class BillingIDValidityMixin(object):

    def __init__(self, *args, **kwargs):
        self.is_billing_id_invalid = False
        super().__init__(*args, **kwargs)

    def validate_billing_id(self, billing_id, ignore_invalid=False):
        if not is_billing_id_valid(billing_id):
            self.is_billing_id_invalid = True
            if not ignore_invalid:
                raise forms.ValidationError(
                    f'Project ID {billing_id} is not currently valid.')


def billing_id_validators():
    """Return a list of validators for billing IDs."""
    return [
        MinLengthValidator(10),
        RegexValidator(
            regex=settings.LBL_BILLING_ID_REGEX,
            message=(
                'Project ID must have six digits, then a hyphen, then three '
                'digits (e.g., 123456-789).')),
    ]


class BillingIDValidationForm(BillingIDValidityMixin, forms.Form):

    billing_id = forms.CharField(
        help_text='Example: 123456-789',
        label='Project ID',
        max_length=10,
        required=True,
        validators=billing_id_validators())

    def __init__(self, *args, **kwargs):
        self.enforce_validity = bool(kwargs.pop('enforce_validity', True))
        super().__init__(*args, **kwargs)

    def clean_billing_id(self):
        """Return the given billing ID if it exists, and optionally, is
        valid. Otherwise, raise a ValidationError."""
        billing_id = self.cleaned_data['billing_id']
        self.validate_billing_id(
            billing_id, ignore_invalid=not self.enforce_validity)
        return billing_id


class BillingIDCreationForm(BillingIDValidityMixin, forms.Form):

    billing_id = forms.CharField(
        help_text='Example: 123456-789',
        label='Project ID',
        max_length=10,
        required=True,
        validators=billing_id_validators())
    ignore_invalid = forms.BooleanField(
        initial=False,
        label='Create the Project ID even if it is invalid.',
        required=False)

    def clean_billing_id(self):
        billing_id = self.cleaned_data['billing_id']
        if not is_billing_id_valid(billing_id):
            return billing_id
        if get_billing_activity_from_full_id(billing_id):
            raise forms.ValidationError(
                f'Project ID {billing_id} already exists.')
        return billing_id

    def clean(self):
        """Disallow invalid billing IDs from being created, unless the
        user explicitly allows it."""
        cleaned_data = super().clean()
        billing_id = cleaned_data.get('billing_id', None)
        if not billing_id:
            # Validation failed.
            return cleaned_data
        ignore_invalid = cleaned_data.get('ignore_invalid')
        self.validate_billing_id(billing_id, ignore_invalid=ignore_invalid)
        return cleaned_data


class BillingIDBaseSetForm(BillingIDValidityMixin, forms.Form):

    billing_activity = BillingActivityChoiceField(
        label='Project ID',
        queryset=BillingActivity.objects.all(),
        required=True)
    ignore_invalid = forms.BooleanField(
        initial=False,
        label='Set the Project ID even if it is invalid.',
        required=False)

    def clean(self):
        """Disallow invalid billing IDs from being set, unless the user
        explicitly allows it."""
        cleaned_data = super().clean()
        billing_activity = cleaned_data.get('billing_activity')
        billing_id = billing_activity.full_id()
        ignore_invalid = cleaned_data.get('ignore_invalid')
        self.validate_billing_id(billing_id, ignore_invalid=ignore_invalid)
        return cleaned_data


class BillingIDSetProjectDefaultForm(BillingIDBaseSetForm):

    project = forms.CharField(
        widget=forms.TextInput(attrs={'readonly': 'readonly'}))

    field_order = ['project', 'billing_activity', 'ignore_invalid']


class BillingIDSetRechargeForm(BillingIDBaseSetForm):

    project = forms.CharField(
        widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    user = forms.CharField(
        widget=forms.TextInput(attrs={'readonly': 'readonly'}))

    field_order = ['project', 'user', 'billing_activity', 'ignore_invalid']


class BillingIDSetUserAccountForm(BillingIDBaseSetForm):

    user = forms.CharField(
        widget=forms.TextInput(attrs={'readonly': 'readonly'}))

    field_order = ['user', 'billing_activity', 'ignore_invalid']


class BillingIDUsagesSearchForm(forms.Form):

    billing_activity = BillingActivityChoiceField(
        help_text=(
            'Filter results to only include usages of the selected ID. If an '
            'ID does not appear in the list, then there are no usages.'),
        label='LBL Project ID',
        queryset=BillingActivity.objects.all(),
        required=False)
    project = forms.ModelChoiceField(
        help_text=(
            'Filter results to include usages of IDs associated with the '
            'selected project.'),
        label='Project',
        queryset=Project.objects.all(),
        required=False)
    user = forms.ModelChoiceField(
        help_text=(
            'Filter results to include usages of IDs associated with the '
            'selected user.'),
        label='User',
        queryset=User.objects.all(),
        required=False)
