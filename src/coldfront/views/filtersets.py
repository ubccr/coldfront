# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import json

import django_filters
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext as _

from coldfront.core.choices import CustomFieldFilterLogicChoices, ObjectChangeActionChoices
from coldfront.core.filters import TagFilter, TagIDFilter
from coldfront.core.models import CustomField, ObjectChange, SavedFilter

__all__ = (
    "BaseFilterSet",
    "ChangeLoggedModelFilterSet",
    "NestedGroupModelFilterSet",
    "OrganizationalModelFilterSet",
    "PrimaryModelFilterSet",
    "AttributeFilterSetMixin",
)


class BaseFilterSet(django_filters.FilterSet):
    """
    A base FilterSet which can extend django-filter2's FilterSet class.
    """

    pass


class ChangeLoggedModelFilterSet(BaseFilterSet):
    """
    Base FilterSet for ChangeLoggedModel classes.
    """

    created = django_filters.DateTimeFilter()
    modified = django_filters.DateTimeFilter()
    created_by_request = django_filters.UUIDFilter(method="filter_by_request")
    updated_by_request = django_filters.UUIDFilter(method="filter_by_request")
    modified_by_request = django_filters.UUIDFilter(method="filter_by_request")

    def filter_by_request(self, queryset, name, value):
        content_type = ContentType.objects.get_for_model(self.Meta.model)
        action = {
            "created_by_request": Q(action=ObjectChangeActionChoices.ACTION_CREATE),
            "updated_by_request": Q(action=ObjectChangeActionChoices.ACTION_UPDATE),
            "modified_by_request": Q(
                action__in=[ObjectChangeActionChoices.ACTION_CREATE, ObjectChangeActionChoices.ACTION_UPDATE]
            ),
        }.get(name)
        request_id = value
        pks = ObjectChange.objects.filter(
            action,
            changed_object_type=content_type,
            request_id=request_id,
        ).values_list("changed_object_id", flat=True)
        return queryset.filter(pk__in=pks)


class ColdFrontModelFilterSet(ChangeLoggedModelFilterSet):
    """
    Provides additional filtering functionality (e.g. tags) for core ColdFront models.
    """

    q = django_filters.CharFilter(
        method="search",
        label=_("Search"),
    )
    tag = TagFilter()
    tag_id = TagIDFilter()

    def __init__(self, *args, **kwargs):
        # Determine the data from positional args (django-filter convention: first arg is data)
        data = args[0] if args else kwargs.get("data")

        # Apply any referenced SavedFilters
        if data is not None and ("filter" in data or "filter_id" in data):
            data = data.copy()  # Get a mutable copy
            saved_filters = SavedFilter.objects.filter(
                Q(slug__in=data.pop("filter", [])) | Q(pk__in=data.pop("filter_id", []))
            )
            for sf in saved_filters:
                for key, value in sf.parameters.items():
                    # QueryDicts are... fun
                    if type(value) not in (list, tuple):
                        value = [value]
                    if key in data:
                        for v in value:
                            data.appendlist(key, v)
                    else:
                        data.setlist(key, value)

            # Replace the original data with the merged copy when forwarding to parent
            if args:
                args = (data,) + args[1:]
            else:
                kwargs["data"] = data

        super().__init__(*args, **kwargs)

        custom_field_filters = {}
        for custom_field in CustomField.objects.get_for_model(self._meta.model):
            if custom_field.filter_logic == CustomFieldFilterLogicChoices.FILTER_DISABLED:
                # Skip disabled fields
                continue
            if filter_instance := custom_field.to_filter():
                filter_name = f"cf_{custom_field.name}"
                custom_field_filters[filter_name] = filter_instance

                # Add relevant additional lookups
                # additional_lookups = self.get_additional_lookups(filter_name, filter_instance)
                # custom_field_filters.update(additional_lookups)

        self.filters.update(custom_field_filters)

    def search(self, queryset, name, value):
        """
        Override this method to apply a general-purpose search logic.
        """
        return queryset


class PrimaryModelFilterSet(ColdFrontModelFilterSet):
    """
    Base filterset for models inheriting from PrimaryModel.
    """

    pass


class OrganizationalModelFilterSet(ColdFrontModelFilterSet):
    """
    Base filterset for models inheriting from OrganizationalModel.
    """

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(models.Q(name__icontains=value) | models.Q(description__icontains=value))


class NestedGroupModelFilterSet(ColdFrontModelFilterSet):
    """
    Base filterset for models inheriting from NestedGroupModel.
    """

    def search(self, queryset, name, value):
        if value.strip():
            queryset = queryset.filter(
                models.Q(name__icontains=value)
                | models.Q(slug__icontains=value)
                | models.Q(description__icontains=value)
            )

        return queryset


class AttributeFilterSetMixin:
    attributes_field_name = "attribute_data"
    attribute_filter_prefix = "attr_"

    def __init__(self, data=None, queryset=None, *, request=None, prefix=None):
        self.attr_filters = {}

        # Extract JSONField-based filters from the incoming data
        if data is not None:
            for key, value in data.items():
                if field := self._get_field_lookup(key):
                    # Attempt to cast the value to a native JSON type
                    try:
                        self.attr_filters[field] = json.loads(value)
                    except (ValueError, json.JSONDecodeError):
                        self.attr_filters[field] = value

        super().__init__(data=data, queryset=queryset, request=request, prefix=prefix)

    def _get_field_lookup(self, key):
        if not key.startswith(self.attribute_filter_prefix):
            return None
        lookup = key.split(self.attribute_filter_prefix, 1)[1]  # Strip prefix
        return f"{self.attributes_field_name}__{lookup}"

    def filter_queryset(self, queryset):
        return super().filter_queryset(queryset).filter(**self.attr_filters)
