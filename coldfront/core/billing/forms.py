from coldfront.core.billing.models import BillingActivity

from django import forms
from django.conf import settings
from django.core.validators import MinLengthValidator
from django.core.validators import RegexValidator


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
        try:
            billing_activity = BillingActivity.get_from_full_id(billing_id)
        except BillingActivity.DoesNotExist:
            raise forms.ValidationError(
                f'Project ID {billing_id} does not currently exist.')
        # TODO: Enforce validity. BillingActivity no longer has is_valid.
        # if self.enforce_validity and not billing_activity.is_valid:
        #     raise forms.ValidationError(
        #         f'Project ID {billing_id} is not currently valid.')
        return billing_activity
