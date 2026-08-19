# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import django_filters
from django.db.models import Q
from django.utils.translation import gettext as _

from coldfront.billing.choices import (
    ChargeBasisChoices,
    DiscountTypeChoices,
    InvoiceLineTypeChoices,
    InvoiceStatusChoices,
    UnitFormatChoiceSet,
)
from coldfront.billing.models import (
    Discount,
    FreeAllowance,
    Invoice,
    InvoiceLineItem,
    Rate,
)
from coldfront.ras.models import Project
from coldfront.users.models import User
from coldfront.views.filtersets import ChangeLoggedModelFilterSet, PrimaryModelFilterSet


class InvoiceFilterSet(PrimaryModelFilterSet):
    owner_id = django_filters.ModelMultipleChoiceFilter(
        queryset=User.objects.all(),
        distinct=False,
        label=_("Owner (ID)"),
    )
    owner = django_filters.ModelMultipleChoiceFilter(
        field_name="owner__username",
        queryset=User.objects.all(),
        distinct=False,
        to_field_name="username",
        label=_("Owner (username)"),
    )
    projects_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Project.objects.all(),
        distinct=False,
        label=_("Projects (ID)"),
    )
    status = django_filters.ChoiceFilter(
        choices=InvoiceStatusChoices,
    )

    class Meta:
        model = Invoice
        fields = (
            "id",
            "owner",
            "projects_id",
            "status",
            "start_date",
            "end_date",
            "due_date",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(slug__icontains=value) | Q(owner__username__icontains=value) | Q(description__icontains=value)
        )


class InvoiceLineItemFilterSet(ChangeLoggedModelFilterSet):
    invoice_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Invoice.objects.all(),
        distinct=False,
        label=_("Invoice (ID)"),
    )
    line_type = django_filters.ChoiceFilter(
        choices=InvoiceLineTypeChoices,
    )
    unit_format = django_filters.ChoiceFilter(
        choices=UnitFormatChoiceSet,
        label=_("Unit label"),
    )

    class Meta:
        model = InvoiceLineItem
        fields = (
            "id",
            "invoice_id",
            "line_type",
            "unit_format",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(description__icontains=value))


class RateFilterSet(PrimaryModelFilterSet):
    unit_format = django_filters.ChoiceFilter(
        choices=UnitFormatChoiceSet,
        label=_("Unit label"),
    )
    charge_basis = django_filters.ChoiceFilter(
        choices=ChargeBasisChoices,
    )

    class Meta:
        model = Rate
        fields = (
            "id",
            "unit_format",
            "charge_basis",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(description__icontains=value))


class FreeAllowanceFilterSet(PrimaryModelFilterSet):
    owner_id = django_filters.ModelMultipleChoiceFilter(
        queryset=User.objects.all(),
        distinct=False,
        label=_("Owner (ID)"),
    )
    owner = django_filters.ModelMultipleChoiceFilter(
        field_name="owner__username",
        queryset=User.objects.all(),
        distinct=False,
        to_field_name="username",
        label=_("Owner (username)"),
    )
    project_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Project.objects.all(),
        distinct=False,
        label=_("Project (ID)"),
    )
    project = django_filters.ModelMultipleChoiceFilter(
        field_name="project__name",
        queryset=Project.objects.all(),
        distinct=False,
        to_field_name="name",
        label=_("Project (name)"),
    )
    unit_format = django_filters.ChoiceFilter(
        choices=UnitFormatChoiceSet,
        label=_("Unit label"),
    )

    class Meta:
        model = FreeAllowance
        fields = (
            "id",
            "owner",
            "project",
            "unit_format",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(owner__username__icontains=value) | Q(description__icontains=value))


class DiscountFilterSet(PrimaryModelFilterSet):
    owner_id = django_filters.ModelMultipleChoiceFilter(
        queryset=User.objects.all(),
        distinct=False,
        label=_("Owner (ID)"),
    )
    owner = django_filters.ModelMultipleChoiceFilter(
        field_name="owner__username",
        queryset=User.objects.all(),
        distinct=False,
        to_field_name="username",
        label=_("Owner (username)"),
    )
    project_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Project.objects.all(),
        distinct=False,
        label=_("Project (ID)"),
    )
    project = django_filters.ModelMultipleChoiceFilter(
        field_name="project__name",
        queryset=Project.objects.all(),
        distinct=False,
        to_field_name="name",
        label=_("Project (name)"),
    )
    type = django_filters.ChoiceFilter(
        choices=DiscountTypeChoices,
    )

    class Meta:
        model = Discount
        fields = (
            "id",
            "owner",
            "project",
            "type",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(owner__username__icontains=value) | Q(description__icontains=value))
