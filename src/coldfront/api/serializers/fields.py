# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.relations import PrimaryKeyRelatedField, RelatedField

from coldfront.models.utils import get_default_currency
from coldfront.views import get_viewname


class BaseColdFrontHyperlinkedIdentityField(serializers.HyperlinkedIdentityField):
    """
    Overrides HyperlinkedIdentityField to use standard ColdFront view naming
    instead of passing in the view_name.  Initialize with a blank view_name
    and it will get replaced in the get_url call.  Derived classes must
    define a get_view_name.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(view_name="", *args, **kwargs)

    def get_url(self, obj, view_name, request, format):
        """
        Given an object, return the URL that hyperlinks to the object.

        May raise a `NoReverseMatch` if the `view_name` and `lookup_field`
        attributes are not configured to correctly match the URL conf.
        """
        # Unsaved objects will not yet have a valid URL.
        if hasattr(obj, "pk") and obj.pk in (None, ""):
            return None

        lookup_value = getattr(obj, self.lookup_field)
        kwargs = {self.lookup_url_kwarg: lookup_value}

        view_name = self.get_view_name(obj)
        return self.reverse(view_name, kwargs=kwargs, request=request, format=format)

    def get_view_name(self, model):
        raise NotImplementedError(
            _("{class_name} must implement get_view_name()").format(class_name=self.__class__.__name__)
        )


class ColdFrontAPIHyperlinkedIdentityField(BaseColdFrontHyperlinkedIdentityField):
    def get_view_name(self, model):
        return get_viewname(model=model, action="detail", rest_api=True)


class ColdFrontURLHyperlinkedIdentityField(BaseColdFrontHyperlinkedIdentityField):
    def get_view_name(self, model):
        return get_viewname(model=model)


class SerializedPKRelatedField(PrimaryKeyRelatedField):
    """
    Extends PrimaryKeyRelatedField to return a serialized object on read. This is useful for representing related
    objects in a ManyToManyField while still allowing a set of primary keys to be written.
    """

    def __init__(self, serializer, nested=False, **kwargs):
        self.serializer = serializer
        self.nested = nested
        self.pk_field = kwargs.pop("pk_field", None)

        super().__init__(**kwargs)

    def to_representation(self, value):
        return self.serializer(value, nested=self.nested, context={"request": self.context["request"]}).data


@extend_schema_field(OpenApiTypes.STR)
class ContentTypeField(RelatedField):
    """
    Represent a ContentType as '<app_label>.<model>'
    """

    default_error_messages = {
        "does_not_exist": _("Invalid content type: {content_type}"),
        "invalid": _("Invalid value. Specify a content type as '<app_label>.<model_name>'."),
    }

    def to_internal_value(self, data):
        try:
            app_label, model = data.split(".")
            return ContentType.objects.get_by_natural_key(app_label=app_label, model=model)
        except ObjectDoesNotExist:
            self.fail("does_not_exist", content_type=data)
        except (AttributeError, TypeError, ValueError):
            self.fail("invalid")

    def to_representation(self, obj):
        return f"{obj.app_label}.{obj.model}"


@extend_schema_field(OpenApiTypes.STR)
class RelatedObjectCountField(serializers.ReadOnlyField):
    """
    Represents a read-only integer count of related objects (e.g. the number of allocations assigned to a project). This field
    is detected by get_annotations_for_serializer() when determining the annotations to be added to a queryset
    depending on the serializer fields selected for inclusion in the response.
    """

    def __init__(self, relation, **kwargs):
        self.relation = relation

        super().__init__(**kwargs)


class ChoiceField(serializers.Field):
    """
    Represent a ChoiceField as {'value': <DB value>, 'label': <string>}. Accepts a single value on write.

    :param choices: An iterable of choices in the form (value, key).
    :param allow_blank: Allow blank values in addition to the listed choices.
    """

    def __init__(self, choices, allow_blank=False, **kwargs):
        self.choiceset = choices
        self.allow_blank = allow_blank
        self._choices = dict()

        # Unpack grouped choices
        for k, v in choices:
            if type(v) in [list, tuple]:
                for k2, v2 in v:
                    self._choices[k2] = v2
            else:
                self._choices[k] = v

        super().__init__(**kwargs)

    def validate_empty_values(self, data):
        # Convert null to an empty string unless allow_null == True
        if data is None:
            if self.allow_null:
                return True, None
            data = ""
        return super().validate_empty_values(data)

    def to_representation(self, obj):
        if obj != "":
            # Use an empty string in place of the choice label if it cannot be resolved (i.e. because a previously
            # configured choice has been removed from FIELD_CHOICES).
            return {
                "value": obj,
                "label": self._choices.get(obj, ""),
            }
        return None

    def to_internal_value(self, data):
        if data == "":
            if self.allow_blank:
                return data
            raise ValidationError(_("This field may not be blank."))

        # Provide an explicit error message if the request is trying to write a dict or list
        if isinstance(data, (dict, list)):
            raise ValidationError(
                _('Value must be passed directly (e.g. "foo": 123); do not use a dictionary or list.')
            )

        # Check for string representations of boolean/integer values
        if hasattr(data, "lower"):
            if data.lower() == "true":
                data = True
            elif data.lower() == "false":
                data = False
            else:
                try:
                    data = int(data)
                except ValueError:
                    pass

        try:
            if data in self._choices:
                return data
        except TypeError:  # Input is an unhashable type
            pass

        raise ValidationError(_("{value} is not a valid choice.").format(value=data))

    @property
    def choices(self):
        return self._choices


class AttributesField(serializers.JSONField):
    """
    Custom attributes stored as JSON data.
    """

    def to_internal_value(self, data):
        data = super().to_internal_value(data)

        # If updating an object, start with the initial attribute data. This enables the client to modify
        # individual attributes without having to rewrite the entire field.
        if data and self.parent.instance:
            initial_data = getattr(self.parent.instance, self.source, None) or {}
            return {**initial_data, **data}

        return data


class MoneyField(serializers.Field):
    """
    Serializes a django-money ``Money`` value as a numeric amount.

    On read, a ``Money`` instance is rendered as its Decimal amount. On write,
    accepts either a bare amount (``10000.00`` / ``"10000.00"``, using
    ``default_currency``) or an amount plus currency (a two-item list/tuple or
    a ``{"amount": ..., "currency": ...}`` dict). Returns a ``Money`` instance
    so the model's MoneyField persists both the amount and its currency.
    Unsupported currency codes are rejected.
    """

    default_error_messages = {
        "invalid": _("Enter a valid number or a money value."),
        "unsupported_currency": _("Unsupported currency code: {currency}"),
    }

    def __init__(self, *args, **kwargs):
        self.default_currency = get_default_currency()
        super().__init__(*args, **kwargs)

    def to_representation(self, value):
        if value is None:
            return None
        # value may be a Money instance or a bare Decimal/str from a model read.
        amount = getattr(value, "amount", value)
        return amount

    def to_internal_value(self, data):
        if data is None:
            return None
        currency = self.default_currency
        amount = data
        if isinstance(data, (list, tuple)):
            if len(data) != 2:
                self.fail("invalid")
            amount, currency = data
        elif isinstance(data, dict):
            amount = data.get("amount")
            currency = data.get("currency", self.default_currency)

        try:
            from decimal import Decimal

            amount = Decimal(str(amount))
        except Exception:
            self.fail("invalid")

        try:
            from djmoney.money import Money

            return Money(amount, currency)
        except Exception:
            self.fail("unsupported_currency", currency=currency)
