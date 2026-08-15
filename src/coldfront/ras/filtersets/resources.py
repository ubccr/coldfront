# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import django_filters
from django.db.models import Q
from django.utils.translation import gettext as _

from coldfront.core.choices import ColorChoices
from coldfront.ras.choices import ResourceStatusChoices
from coldfront.ras.models import Resource, ResourceType
from coldfront.tenancy.filtersets import TenancyFilterSet
from coldfront.views.filtersets import AttributeFilterSetMixin, NestedGroupModelFilterSet, OrganizationalModelFilterSet


class ResourceTypeFilterSet(OrganizationalModelFilterSet):
    color = django_filters.MultipleChoiceFilter(
        choices=ColorChoices.CHOICES,
    )

    class Meta:
        model = ResourceType
        fields = (
            "id",
            "name",
            "slug",
            "color",
            "description",
        )


class ResourceFilterSet(AttributeFilterSetMixin, TenancyFilterSet, NestedGroupModelFilterSet):
    resource_type_id = django_filters.ModelMultipleChoiceFilter(
        queryset=ResourceType.objects.all(),
        distinct=False,
        label=_("Resource type (ID)"),
    )
    resource_type = django_filters.ModelMultipleChoiceFilter(
        field_name="resource_type__slug",
        queryset=ResourceType.objects.all(),
        distinct=False,
        to_field_name="slug",
        label=_("Resource type (slug)"),
    )
    parent_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Resource.objects.all(),
        distinct=False,
        label=_("Parent resource (ID)"),
    )
    parent = django_filters.ModelMultipleChoiceFilter(
        field_name="parent__slug",
        queryset=Resource.objects.all(),
        distinct=False,
        to_field_name="slug",
        label=_("Parent resource (slug)"),
    )
    status = django_filters.MultipleChoiceFilter(
        choices=ResourceStatusChoices,
        distinct=False,
        null_value=None,
    )

    class Meta:
        model = Resource
        fields = (
            "id",
            "name",
            "slug",
            "status",
            "resource_type",
            "parent",
            "description",
            "locked",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(name__icontains=value) | Q(description__icontains=value))
