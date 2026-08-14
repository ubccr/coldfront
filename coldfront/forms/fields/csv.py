# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from decimal import Decimal

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldError, MultipleObjectsReturned, ObjectDoesNotExist
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from djmoney.money import Money

from coldfront.choices import unpack_grouped_choices
from coldfront.core.models import ObjectType
from coldfront.models.utils import get_default_currency


class CSVSelectWidget(forms.Select):
    """
    Custom Select widget for CSV imports that treats blank values as omitted.
    This allows model defaults to be applied when a CSV field is present but empty.
    """

    def value_omitted_from_data(self, data, files, name):
        # Check if value is omitted using parent behavior
        if super().value_omitted_from_data(data, files, name):
            return True
        # Treat blank/empty strings as omitted to allow model defaults
        value = data.get(name)
        return value == "" or value is None


class CSVChoicesMixin:
    STATIC_CHOICES = True

    def __init__(self, *, choices=(), **kwargs):
        super().__init__(choices=choices, **kwargs)
        self.choices = unpack_grouped_choices(choices)


class CSVChoiceField(CSVChoicesMixin, forms.ChoiceField):
    """
    A CSV field which accepts a single selection value.
    Treats blank CSV values as omitted to allow model defaults.
    """

    widget = CSVSelectWidget


class CSVMultipleChoiceField(CSVChoicesMixin, forms.MultipleChoiceField):
    """
    A CSV field which accepts multiple selection values.
    """

    def to_python(self, value):
        if not value:
            return []
        if not isinstance(value, str):
            raise forms.ValidationError(_("Invalid value for a multiple choice field: {value}").format(value=value))
        return value.split(",")


class CSVTypedChoiceField(forms.TypedChoiceField):
    """
    A CSV field for typed choice values.
    Treats blank CSV values as omitted to allow model defaults.
    """

    STATIC_CHOICES = True
    widget = CSVSelectWidget


class CSVModelChoiceField(forms.ModelChoiceField):
    """
    Extends Django's `ModelChoiceField` to provide additional validation for CSV values.
    """

    default_error_messages = {
        "invalid_choice": _("Object not found: %(value)s"),
    }

    def to_python(self, value):
        try:
            return super().to_python(value)
        except MultipleObjectsReturned:
            raise forms.ValidationError(
                _('"{value}" is not a unique value for this field; multiple objects were found').format(value=value)
            )
        except FieldError:
            raise forms.ValidationError(
                _('"{field_name}" is an invalid accessor field name.').format(field_name=self.to_field_name)
            )


class CSVModelMultipleChoiceField(forms.ModelMultipleChoiceField):
    """
    Extends Django's `ModelMultipleChoiceField` to support comma-separated values.
    """

    default_error_messages = {
        "invalid_choice": _("Object not found: %(value)s"),
    }

    def clean(self, value):
        if not isinstance(value, list):
            value = value.split(",") if value else []
        return super().clean(value)


class CSVContentTypeField(CSVModelChoiceField):
    """
    CSV field for referencing a single content type, in the form `<app>.<model>`.
    """

    STATIC_CHOICES = True

    def prepare_value(self, value):
        return ObjectType.identifier_string(value)

    def to_python(self, value):
        if not value:
            return None
        try:
            app_label, model = value.split(".")
        except ValueError:
            raise forms.ValidationError(_('Object type must be specified as "<app>.<model>"'))
        try:
            return self.queryset.get(app_label=app_label, model=model)
        except ObjectDoesNotExist:
            raise forms.ValidationError(_("Invalid object type"))


class CSVMultipleContentTypeField(forms.ModelMultipleChoiceField):
    """
    CSV field for referencing one or more content types, in the form `<app>.<model>`.
    """

    STATIC_CHOICES = True

    # TODO: Improve validation of selected ContentTypes
    def prepare_value(self, value):
        if not value:
            return None
        if type(value) is str:
            ct_filter = Q()
            for name in value.split(","):
                try:
                    app_label, model = name.split(".")
                    ct_filter |= Q(app_label=app_label, model=model)
                except ValueError:
                    raise forms.ValidationError(_("Invalid object type"))
            return list(ContentType.objects.filter(ct_filter).values_list("pk", flat=True))
        return ObjectType.identifier_string(value)


class CSVContentTypeObjectField(forms.Field):
    """
    CSV field for referencing a generic object by content type and identifier.

    Accepts values in the format `<app_label>.<model>:<identifier_value>`, where the
    identifier value is used to look up the object by its `to_field_name` (defaults to `name`).
    For example: `ras.resource:My Cluster` would look up a Resource with name "My Cluster".
    """

    default_error_messages = {
        "invalid_choice": _("Object not found: %(value)s"),
    }

    def __init__(self, *, to_field_name="name", **kwargs):
        self.to_field_name = to_field_name
        kwargs.setdefault("required", True)
        super().__init__(**kwargs)

    def to_python(self, value):
        if not value:
            return None
        try:
            # Parse the format <app_label>.<model>:<identifier_value>
            # Support both <app_label>.<model>:<value> and <app_label>.<model>:<field>=<value>
            ct_part, _, identifier_part = value.partition(":")
            if not identifier_part:
                raise forms.ValidationError(_('Value must be in the format "<app_label>.<model>:<identifier>"'))
            app_label, model = ct_part.split(".")
        except ValueError:
            raise forms.ValidationError(_('Value must be in the format "<app_label>.<model>:<identifier>"'))

        # Resolve the ContentType and model class
        try:
            ct = ContentType.objects.get_by_natural_key(app_label=app_label, model=model)
        except ObjectDoesNotExist:
            raise forms.ValidationError(
                _('Invalid content type: "{app_label}.{model}"').format(app_label=app_label, model=model)
            )

        model_class = ct.model_class()
        if model_class is None:
            raise forms.ValidationError(_("Model class not found for content type"))

        # Check if the identifier uses a specific field: <field>=<value>
        if "=" in identifier_part:
            field_name, _, field_value = identifier_part.partition("=")
            field_name = field_name.strip()
            field_value = field_value.strip()
        else:
            field_name = self.to_field_name
            field_value = identifier_part.strip()

        # Look up the object
        try:
            filter_kwargs = {field_name: field_value}
            obj = model_class.objects.get(**filter_kwargs)
        except ObjectDoesNotExist:
            raise forms.ValidationError(_("Object not found: {value}").format(value=value))
        except MultipleObjectsReturned:
            raise forms.ValidationError(_('"{value}" matched multiple objects').format(value=value))

        return obj


class CSVMoneyField(forms.Field):
    """
    A CSV field which parses a single money value into a ``Money`` instance.

    Accepts a bare amount ("10000.00", using ``default_currency``) or an amount
    plus currency ("10000.00 USD"). Blank values are treated as omitted (None)
    so model defaults apply. Unknown currency codes are rejected.
    """

    def __init__(self, *, max_digits=14, decimal_places=2, **kwargs):
        self.default_currency = get_default_currency()
        self.max_digits = max_digits
        self.decimal_places = decimal_places
        super().__init__(**kwargs)

    def to_python(self, value):
        if value in (None, ""):
            return None
        if not isinstance(value, str):
            raise forms.ValidationError(_("Invalid money value: {value}").format(value=value))
        value = value.strip()
        if " " in value:
            amount, currency = value.rsplit(" ", 1)
        else:
            amount, currency = value, self.default_currency
        try:
            amount = Decimal(amount)
        except Exception:
            raise forms.ValidationError(_("Invalid money amount: {value}").format(value=value))
        try:
            return Money(amount, currency)
        except Exception:
            raise forms.ValidationError(_("Unsupported currency code: {currency}").format(currency=currency))
