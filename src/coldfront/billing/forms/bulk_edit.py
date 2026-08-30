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
    PaymentMethodChoices,
    UnitFormatChoiceSet,
)
from coldfront.billing.models import (
    Discount,
    FreeAllowance,
    Invoice,
    InvoiceLineItem,
    Rate,
)
from coldfront.forms import ColdFrontModelBulkEditForm, PrimaryModelBulkEditForm
from coldfront.forms.fields import MoneyField
from coldfront.forms.fields.bytes import BytesField
from coldfront.users.models import User
from coldfront.utils.forms import add_blank_choice

__all__ = (
    "DiscountBulkEditForm",
    "FreeAllowanceBulkEditForm",
    "InvoiceBulkEditForm",
    "InvoiceLineItemBulkEditForm",
    "RateBulkEditForm",
)


class InvoiceBulkEditForm(PrimaryModelBulkEditForm):
    owner = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        label=_("Owner"),
    )
    status = forms.ChoiceField(
        choices=add_blank_choice(InvoiceStatusChoices),
        required=False,
        label=_("Status"),
    )
    payment_method = forms.ChoiceField(
        choices=add_blank_choice(PaymentMethodChoices),
        required=False,
        label=_("Payment method"),
    )
    payment_amount = MoneyField(
        required=False,
        max_digits=14,
        decimal_places=2,
        label=_("Payment amount"),
    )
    subtotal = MoneyField(
        required=False,
        max_digits=14,
        decimal_places=2,
        label=_("Subtotal"),
    )
    allowance_total = MoneyField(
        required=False,
        max_digits=14,
        decimal_places=2,
        label=_("Allowance total"),
    )
    discount_total = MoneyField(
        required=False,
        max_digits=14,
        decimal_places=2,
        label=_("Discount total"),
    )
    grand_total = MoneyField(
        required=False,
        max_digits=14,
        decimal_places=2,
        label=_("Grand total"),
    )

    model = Invoice
    nullable_fields = (
        "payment_date",
        "payment_amount",
        "payment_method",
        "subtotal",
        "allowance_total",
        "discount_total",
        "grand_total",
    )

    @property
    def fieldsets(self):
        return [
            Fieldset(
                _("Invoice"),
                "owner",
                "status",
                "description",
            ),
            Fieldset(
                _("Payment"),
                "payment_amount",
                "payment_method",
            ),
            Fieldset(
                _("Totals"),
                "subtotal",
                "allowance_total",
                "discount_total",
                "grand_total",
            ),
        ]


class InvoiceLineItemBulkEditForm(ColdFrontModelBulkEditForm):
    invoice = forms.ModelChoiceField(
        queryset=Invoice.objects.all(),
        required=False,
        label=_("Invoice"),
    )
    line_type = forms.ChoiceField(
        choices=add_blank_choice(InvoiceLineTypeChoices),
        required=False,
        label=_("Line type"),
    )
    description = forms.CharField(
        max_length=100,
        required=False,
        label=_("Description"),
    )
    unit = forms.CharField(
        max_length=50,
        required=False,
        label=_("Unit"),
    )
    unit_format = forms.ChoiceField(
        choices=add_blank_choice(UnitFormatChoiceSet),
        required=False,
        label=_("Unit label"),
    )
    unit_price = MoneyField(
        required=False,
        max_digits=14,
        decimal_places=2,
        label=_("Unit price"),
    )
    amount = MoneyField(
        required=False,
        max_digits=14,
        decimal_places=2,
        label=_("Amount"),
    )

    model = InvoiceLineItem
    nullable_fields = (
        "unit",
        "unit_price",
        "amount",
    )

    @property
    def fieldsets(self):
        return [
            Fieldset(
                _("Invoice Line Item"),
                "invoice",
                "line_type",
                "description",
                "unit",
                "unit_format",
                "unit_price",
                "amount",
            ),
        ]


class RateBulkEditForm(PrimaryModelBulkEditForm):
    unit = BytesField(
        required=False,
        label=_("Unit"),
        help_text=_(
            "Native units per billed unit (the divisor). e.g. '1 TB' for per-TB pricing, or '1' for per-SU/per-item."
        ),
    )
    unit_format = forms.ChoiceField(
        choices=add_blank_choice(UnitFormatChoiceSet),
        required=False,
        label=_("Unit label"),
        help_text=_("The native unit dimension this rate prices"),
    )
    amount = MoneyField(
        required=False,
        max_digits=14,
        decimal_places=2,
        label=_("Amount"),
    )
    charge_basis = forms.ChoiceField(
        choices=add_blank_choice(ChargeBasisChoices),
        required=False,
        label=_("Charge basis"),
    )

    model = Rate
    nullable_fields = (
        "amount",
        "effective_start",
        "effective_end",
    )

    @property
    def fieldsets(self):
        return [
            Fieldset(
                _("Rate"),
                "unit",
                "unit_format",
                "amount",
                "charge_basis",
                "description",
            ),
        ]


class FreeAllowanceBulkEditForm(PrimaryModelBulkEditForm):
    owner = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        label=_("Owner"),
    )
    unit_format = forms.ChoiceField(
        choices=add_blank_choice(UnitFormatChoiceSet),
        required=False,
        label=_("Unit label"),
        help_text=_("The native unit dimension of the allowance"),
    )
    quantity_total = BytesField(
        required=False,
        label=_("Total quantity"),
        help_text=_("Total free units granted, in native units. e.g. '10 TB' or '100'."),
    )

    model = FreeAllowance
    nullable_fields = ("used",)

    @property
    def fieldsets(self):
        return [
            Fieldset(
                _("Free Allowance"),
                "owner",
                "unit_format",
                "quantity_total",
                "description",
            ),
        ]


class DiscountBulkEditForm(PrimaryModelBulkEditForm):
    owner = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        label=_("Owner"),
    )
    type = forms.ChoiceField(
        choices=add_blank_choice(DiscountTypeChoices),
        required=False,
        label=_("Type"),
    )
    value = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        label=_("Value"),
    )

    model = Discount
    nullable_fields = ("value",)

    @property
    def fieldsets(self):
        return [
            Fieldset(
                _("Discount"),
                "owner",
                "type",
                "value",
                "description",
            ),
        ]
