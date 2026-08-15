# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import django_filters
from django.db.models import Q
from django.utils.translation import gettext as _

from coldfront.core.models import ObjectType
from coldfront.ras.models import Allocation, Project
from coldfront.tenancy.filtersets import TenancyFilterSet
from coldfront.views.filtersets import AttributeFilterSetMixin, PrimaryModelFilterSet


class AllocationFilterSet(AttributeFilterSetMixin, TenancyFilterSet, PrimaryModelFilterSet):
    resource_name = django_filters.CharFilter(
        method="filter_resource_name",
        label=_("Resource name"),
    )
    project_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Project.objects.all(),
        distinct=False,
        label=_("Projects"),
    )
    resource_object_type_id = django_filters.ModelChoiceFilter(
        field_name="resource_object_type",
        queryset=ObjectType.objects.with_feature("allocatable_resource"),
        label=_("Resource Object"),
    )
    start_date = django_filters.DateFilter(
        field_name="start_date",
        lookup_expr="gte",
        label=_("Start date (on or after)"),
    )
    end_date = django_filters.DateFilter(
        field_name="end_date",
        lookup_expr="lte",
        label=_("End date (on or before)"),
    )

    class Meta:
        model = Allocation
        fields = (
            "id",
            "status",
            "project_id",
            "owner",
            "resource_name",
            "resource_object_type_id",
            "start_date",
            "end_date",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        q = Q(
            Q(owner__username__icontains=value)
            | Q(project__name__icontains=value)
            | Q(justification__icontains=value)
            | Q(description__icontains=value)
        )
        # Also search by resource name
        q |= self._build_resource_name_q(value)
        return queryset.filter(q)

    def filter_resource_name(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(self._build_resource_name_q(value))

    def _build_resource_name_q(self, value):
        """
        Build a Q expression filtering allocations by resource name across all
        resource types that have the "allocatable_resource" feature. All such
        models have a ``name`` field defined by ``AllocatableResourceMixin``.
        """
        q = Q()

        for ot in ObjectType.objects.with_feature("allocatable_resource"):
            model = ot.model_class()
            if model is None:
                continue
            pks = list(model.objects.filter(name__icontains=value).values_list("pk", flat=True))
            if pks:
                q |= Q(
                    resource_object_type=ot,
                    resource_object_id__in=pks,
                )

        return q
