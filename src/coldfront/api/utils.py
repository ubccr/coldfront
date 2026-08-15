# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.exceptions import (
    FieldDoesNotExist,
    FieldError,
    MultipleObjectsReturned,
    ObjectDoesNotExist,
    ValidationError,
)
from django.db.models.fields.related import ManyToOneRel, RelatedField
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _
from rest_framework.permissions import BasePermission
from rest_framework.serializers import Serializer
from rest_framework.views import get_view_name as drf_get_view_name

from coldfront.api.serializers.fields import RelatedObjectCountField
from coldfront.utils.query import count_related, dict_to_filter_params
from coldfront.utils.strings import title

from .exceptions import SerializerNotFound


class IsSuperuser(BasePermission):
    """
    Allows access only to superusers.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_superuser)


def get_related_object_by_attrs(queryset, attrs):
    """
    Return an object identified by either a dictionary of attributes or its numeric primary key (ID). This is used
    for referencing related objects when creating/updating objects via the REST API.
    """
    if attrs is None:
        return None

    # Dictionary of related object attributes
    if isinstance(attrs, dict):
        params = dict_to_filter_params(attrs)
        try:
            return queryset.get(**params)
        except ObjectDoesNotExist:
            raise ValidationError(
                _("Related object not found using the provided attributes: {params}").format(params=params)
            )
        except MultipleObjectsReturned:
            raise ValidationError(_("Multiple objects match the provided attributes: {params}").format(params=params))
        except FieldError as e:
            raise ValidationError(e)

    # Integer PK of related object
    try:
        # Cast as integer in case a PK was mistakenly sent as a string
        pk = int(attrs)
    except (TypeError, ValueError):
        raise ValidationError(
            _(
                "Related objects must be referenced by numeric ID or by dictionary of attributes. Received an "
                "unrecognized value: {value}"
            ).format(value=attrs)
        )

    # Look up object by PK
    try:
        return queryset.get(pk=pk)
    except ObjectDoesNotExist:
        raise ValidationError(_("Related object not found using the provided numeric ID: {id}").format(id=pk))


def get_view_name(view):
    """
    Derive the view name from its associated model, if it has one. Fall back to DRF's built-in `get_view_name()`.
    This function is provided to DRF as its VIEW_NAME_FUNCTION.
    """
    if hasattr(view, "queryset") and view.queryset is not None:
        # Derive the model name from the queryset.
        name = title(view.queryset.model._meta.verbose_name)
        if suffix := getattr(view, "suffix", None):
            name = f"{name} {suffix}"
        return name

    # Fall back to DRF's default behavior
    return drf_get_view_name(view)


def get_prefetches_for_serializer(serializer_class, fields=None, omit=None):
    """
    Compile and return a list of fields which should be prefetched on the queryset for a serializer.
    """
    if fields is not None and omit is not None:
        raise TypeError("Cannot specify both 'fields' and 'omit' parameters.")

    model = serializer_class.Meta.model

    # If fields are not specified, default to all
    fields_to_include = fields or serializer_class.Meta.fields
    fields_to_omit = omit or []

    prefetch_fields = []
    for field_name in fields_to_include:
        if field_name in fields_to_omit:
            continue
        serializer_field = serializer_class._declared_fields.get(field_name)

        # Determine the name of the model field referenced by the serializer field
        model_field_name = field_name
        if serializer_field and serializer_field.source:
            model_field_name = serializer_field.source

        # If the serializer field does not map to a discrete model field, skip it.
        try:
            field = model._meta.get_field(model_field_name)
            if isinstance(field, (RelatedField, ManyToOneRel, GenericForeignKey)):
                prefetch_fields.append(field.name)
        except FieldDoesNotExist:
            continue

        # If this field is represented by a nested serializer, recurse to resolve prefetches
        # for the related object.
        if serializer_field:
            if issubclass(type(serializer_field), Serializer):
                # Determine which fields to prefetch for the nested object
                subfields = serializer_field.Meta.brief_fields if serializer_field.nested else None
                for subfield in get_prefetches_for_serializer(type(serializer_field), subfields):
                    prefetch_fields.append(f"{field_name}__{subfield}")

    return prefetch_fields


def get_annotations_for_serializer(serializer_class, fields=None, omit=None):
    """
    Return a mapping of field names to annotations to be applied to the queryset for a serializer.
    """
    if fields is not None and omit is not None:
        raise TypeError("Cannot specify both 'fields' and 'omit' parameters.")

    model = serializer_class.Meta.model

    # If fields are not specified, default to all
    fields_to_include = fields or serializer_class.Meta.fields
    fields_to_omit = omit or []

    annotations = {}
    for field_name, field in serializer_class._declared_fields.items():
        if field_name in fields_to_omit:
            continue
        if field_name in fields_to_include and type(field) is RelatedObjectCountField:
            related_field = getattr(model, field.relation).field
            annotations[field_name] = count_related(related_field.model, related_field.name)

    return annotations


def get_serializer_for_model(model, prefix=""):
    """
    Return the appropriate REST API serializer for the given model.
    """
    app_label, model_name = model._meta.label.split(".")
    serializer_name = f"coldfront.{app_label}.api.serializers.{prefix}{model_name}Serializer"
    try:
        return import_string(serializer_name)
    except ImportError:
        raise SerializerNotFound(f"Could not determine serializer for {app_label}.{model_name} with prefix '{prefix}'")
