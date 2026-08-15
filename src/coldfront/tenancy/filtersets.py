# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import django_filters
from django.db.models import Q
from django.utils.translation import gettext as _

from coldfront.views.filters import TreeNodeMultipleChoiceFilter
from coldfront.views.filtersets import NestedGroupModelFilterSet, PrimaryModelFilterSet

from .models import Tenant, TenantGroup

__all__ = (
    "TenancyFilterSet",
    "TenantFilterSet",
    "TenantGroupFilterSet",
)


class TenantGroupFilterSet(NestedGroupModelFilterSet):
    parent_id = django_filters.ModelMultipleChoiceFilter(
        queryset=TenantGroup.objects.all(),
        label=_("Parent tenant group (ID)"),
    )
    parent = django_filters.ModelMultipleChoiceFilter(
        field_name="parent__slug",
        queryset=TenantGroup.objects.all(),
        to_field_name="slug",
        label=_("Parent tenant group (slug)"),
    )
    ancestor_id = TreeNodeMultipleChoiceFilter(
        queryset=TenantGroup.objects.all(),
        field_name="parent",
        lookup_expr="in",
        label=_("Tenant group (ID)"),
    )
    ancestor = TreeNodeMultipleChoiceFilter(
        queryset=TenantGroup.objects.all(),
        field_name="parent",
        lookup_expr="in",
        to_field_name="slug",
        label=_("Tenant group (slug)"),
    )

    class Meta:
        model = TenantGroup
        fields = (
            "id",
            "name",
            "slug",
            "description",
        )


class TenantFilterSet(PrimaryModelFilterSet):
    group_id = TreeNodeMultipleChoiceFilter(
        queryset=TenantGroup.objects.all(),
        field_name="group",
        lookup_expr="in",
        label=_("Tenant group (ID)"),
    )
    group = TreeNodeMultipleChoiceFilter(
        queryset=TenantGroup.objects.all(),
        field_name="group",
        lookup_expr="in",
        to_field_name="slug",
        label=_("Tenant group (slug)"),
    )

    class Meta:
        model = Tenant
        fields = (
            "id",
            "name",
            "slug",
            "description",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(name__icontains=value) | Q(slug__icontains=value) | Q(description__icontains=value))


class TenancyFilterSet(django_filters.FilterSet):
    """
    An inheritable FilterSet for models which support Tenant assignment.
    """

    tenant_group_id = TreeNodeMultipleChoiceFilter(
        queryset=TenantGroup.objects.all(),
        field_name="tenant__group",
        lookup_expr="in",
        label=_("Tenant Group (ID)"),
    )
    tenant_group = TreeNodeMultipleChoiceFilter(
        queryset=TenantGroup.objects.all(),
        field_name="tenant__group",
        to_field_name="slug",
        lookup_expr="in",
        label=_("Tenant Group (slug)"),
    )
    tenant_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Tenant.objects.all(),
        label=_("Tenant (ID)"),
    )
    tenant = django_filters.ModelMultipleChoiceFilter(
        queryset=Tenant.objects.all(),
        field_name="tenant__slug",
        to_field_name="slug",
        label=_("Tenant (slug)"),
    )
