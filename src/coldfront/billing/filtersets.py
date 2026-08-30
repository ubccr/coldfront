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
    status = django_filters.ChoiceFilter(
        choices=InvoiceStatusChoices,
    )

    class Meta:
        model = Invoice
        fields = (
            "id",
            "owner",
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
            "name",
            "unit_format",
            "charge_basis",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(name__icontains=value) | Q(description__icontains=value))


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
    unit_format = django_filters.ChoiceFilter(
        choices=UnitFormatChoiceSet,
        label=_("Unit label"),
    )

    class Meta:
        model = FreeAllowance
        fields = (
            "id",
            "name",
            "owner",
            "unit_format",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value) | Q(owner__username__icontains=value) | Q(description__icontains=value)
        )


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
    scope_object_id = django_filters.NumberFilter(
        field_name="scope_object_id",
        label=_("Scope object ID"),
    )
    type = django_filters.ChoiceFilter(
        choices=DiscountTypeChoices,
    )
    global_discount = django_filters.BooleanFilter(
        field_name="owner__isnull",
        label=_("Global (all users)"),
    )

    class Meta:
        model = Discount
        fields = (
            "id",
            "name",
            "owner",
            "scope_object_id",
            "type",
            "global_discount",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value) | Q(owner__username__icontains=value) | Q(description__icontains=value)
        )
