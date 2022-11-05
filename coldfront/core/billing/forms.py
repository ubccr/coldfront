from django import forms
from django.conf import settings
from django.core.validators import MinLengthValidator
from django.core.validators import RegexValidator

from coldfront.core.billing.utils.validation import is_billing_id_valid


# TODO: Replace this module with a directory as needed.


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


class BillingIDValidationForm(forms.Form):

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
        """Return the BillingActivity representing the given billing ID
        if it exists, and optionally, is valid. Otherwise, raise a
        ValidationError."""
        billing_id = self.cleaned_data['billing_id']
        if self.enforce_validity and not is_billing_id_valid(billing_id):
            raise forms.ValidationError(
                f'Project ID {billing_id} is not currently valid.')
        return billing_id
