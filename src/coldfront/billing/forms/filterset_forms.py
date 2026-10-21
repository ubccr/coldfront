# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django import forms
from django.utils.translation import gettext_lazy as _

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
from coldfront.lib.forms import ColdFrontModelFilterSetForm, PrimaryModelFilterSetForm
from coldfront.lib.forms.fields import DynamicModelMultipleChoiceField, TagFilterField
from coldfront.lib.forms.layout import FieldSet
from coldfront.ras.models import Project
from coldfront.users.models import User

__all__ = (
    "DiscountFilterSetForm",
    "FreeAllowanceFilterSetForm",
    "InvoiceFilterSetForm",
    "InvoiceLineItemFilterSetForm",
    "RateFilterSetForm",
)


class InvoiceFilterSetForm(PrimaryModelFilterSetForm):
    model = Invoice
    owner = DynamicModelMultipleChoiceField(
        queryset=User.objects.all(),
        required=False,
        label=_("Owner"),
    )
    projects_id = DynamicModelMultipleChoiceField(
        queryset=Project.objects.all(),
        required=False,
        label=_("Projects"),
    )
    status = forms.MultipleChoiceField(
        label=_("Status"),
        choices=InvoiceStatusChoices,
        required=False,
    )
    tag = TagFilterField(model)

    fieldsets = (
        FieldSet(
            "q",
            "tag",
        ),
        FieldSet(
            "owner",
            "projects_id",
            "status",
            name=_("Invoice"),
        ),
    )


class InvoiceLineItemFilterSetForm(ColdFrontModelFilterSetForm):
    model = InvoiceLineItem
    invoice_id = DynamicModelMultipleChoiceField(
        queryset=Invoice.objects.all(),
        required=False,
        label=_("Invoice"),
    )
    line_type = forms.MultipleChoiceField(
        label=_("Line type"),
        choices=InvoiceLineTypeChoices,
        required=False,
    )
    unit_format = forms.MultipleChoiceField(
        label=_("Unit label"),
        choices=UnitFormatChoiceSet,
        required=False,
    )

    fieldsets = (
        FieldSet(
            "q",
        ),
        FieldSet(
            "invoice_id",
            "line_type",
            "unit_format",
            name=_("Invoice Line Item"),
        ),
    )


class RateFilterSetForm(PrimaryModelFilterSetForm):
    model = Rate
    unit_format = forms.MultipleChoiceField(
        label=_("Unit label"),
        choices=UnitFormatChoiceSet,
        required=False,
    )
    charge_basis = forms.MultipleChoiceField(
        label=_("Charge basis"),
        choices=ChargeBasisChoices,
        required=False,
    )
    project_id = DynamicModelMultipleChoiceField(
        queryset=Project.objects.all(),
        required=False,
        label=_("Project override"),
    )
    tag = TagFilterField(model)

    fieldsets = (
        FieldSet(
            "q",
            "tag",
        ),
        FieldSet(
            "unit_format",
            "charge_basis",
            "project_id",
            name=_("Rate"),
        ),
    )


class FreeAllowanceFilterSetForm(PrimaryModelFilterSetForm):
    model = FreeAllowance
    owner = DynamicModelMultipleChoiceField(
        queryset=User.objects.all(),
        required=False,
        label=_("Owner"),
    )
    project_id = DynamicModelMultipleChoiceField(
        queryset=Project.objects.all(),
        required=False,
        label=_("Project"),
    )
    unit_format = forms.MultipleChoiceField(
        label=_("Unit label"),
        choices=UnitFormatChoiceSet,
        required=False,
    )
    tag = TagFilterField(model)

    fieldsets = (
        FieldSet(
            "q",
            "tag",
        ),
        FieldSet(
            "owner",
            "project_id",
            "unit_format",
            name=_("Free Allowance"),
        ),
    )


class DiscountFilterSetForm(PrimaryModelFilterSetForm):
    model = Discount
    owner = DynamicModelMultipleChoiceField(
        queryset=User.objects.all(),
        required=False,
        label=_("Owner"),
    )
    project_id = DynamicModelMultipleChoiceField(
        queryset=Project.objects.all(),
        required=False,
        label=_("Project"),
    )
    type = forms.MultipleChoiceField(
        label=_("Type"),
        choices=DiscountTypeChoices,
        required=False,
    )
    tag = TagFilterField(model)

    fieldsets = (
        FieldSet(
            "q",
            "tag",
        ),
        FieldSet(
            "owner",
            "project_id",
            "type",
            name=_("Discount"),
        ),
    )
