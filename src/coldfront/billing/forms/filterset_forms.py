# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from crispy_forms.layout import Fieldset
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
from coldfront.forms import ColdFrontModelFilterSetForm, PrimaryModelFilterSetForm
from coldfront.forms.fields import DynamicModelMultipleChoiceField, TagFilterField
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
        Fieldset(
            _("Invoice"),
            "owner",
            "projects_id",
            "status",
            "tag",
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
        Fieldset(
            _("Invoice Line Item"),
            "invoice_id",
            "line_type",
            "unit_format",
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
        Fieldset(
            _("Rate"),
            "unit_format",
            "charge_basis",
            "project_id",
            "tag",
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
        Fieldset(
            _("Free Allowance"),
            "owner",
            "project_id",
            "unit_format",
            "tag",
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
        Fieldset(
            _("Discount"),
            "owner",
            "project_id",
            "type",
            "tag",
        ),
    )
