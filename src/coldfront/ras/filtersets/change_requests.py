# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import django_filters
from django.db.models import Q
from django.utils.translation import gettext as _

from coldfront.ras.models import Allocation
from coldfront.ras.models.change_requests import AllocationChangeRequest
from coldfront.views.filtersets import PrimaryModelFilterSet


class AllocationChangeRequestFilterSet(PrimaryModelFilterSet):
    allocation_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Allocation.objects.all(),
        distinct=False,
        label=_("Allocations"),
    )
    requested_by_id = django_filters.ModelMultipleChoiceFilter(
        queryset=AllocationChangeRequest.objects.all(),
        field_name="requested_by",
        label=_("Requested by"),
    )

    class Meta:
        model = AllocationChangeRequest
        fields = (
            "id",
            "status",
            "allocation_id",
            "requested_by_id",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        q = Q(
            Q(justification__icontains=value)
            | Q(allocation__slug__icontains=value)
            | Q(requested_by__username__icontains=value)
        )
        return queryset.filter(q)
