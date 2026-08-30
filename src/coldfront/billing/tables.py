# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import django_tables2 as tables
from django.utils.translation import gettext_lazy as _

from coldfront.billing.models import (
    Discount,
    FreeAllowance,
    Invoice,
    InvoiceLineItem,
    Rate,
)
from coldfront.tables import ColdFrontTable, PrimaryModelTable, columns

__all__ = (
    "DiscountTable",
    "FreeAllowanceTable",
    "InvoiceLineItemTable",
    "InvoiceTable",
    "RateTable",
)


def _money_column(field, verbose_name):
    """Build a TemplateColumn that renders a django-money field via money_localize."""
    return columns.TemplateColumn(
        template_code="""
            {% load djmoney %}
            {% if record.__FIELD__ %}{% money_localize record.__FIELD__ %} {% else %}—{% endif %}
        """.replace("__FIELD__", field),
        verbose_name=verbose_name,
    )


class InvoiceTable(PrimaryModelTable):
    slug = tables.Column(
        verbose_name=_("Invoice"),
        linkify=True,
    )
    owner = tables.Column(
        verbose_name=_("Owner"),
    )
    status = columns.ChoiceFieldColumn(
        verbose_name=_("Status"),
    )
    due_date = columns.DateColumn(
        verbose_name=_("Due Date"),
    )
    payment_amount = _money_column("payment_amount", _("Payment amount"))
    subtotal = _money_column("subtotal", _("Subtotal"))
    allowance_total = _money_column("allowance_total", _("Allowance total"))
    discount_total = _money_column("discount_total", _("Discount total"))
    grand_total = _money_column("grand_total", _("Grand total"))
    tags = columns.TagColumn(
        url_name="billing:invoice_list",
    )

    class Meta(PrimaryModelTable.Meta):
        model = Invoice
        fields = (
            "pk",
            "id",
            "slug",
            "owner",
            "status",
            "start_date",
            "end_date",
            "due_date",
            "payment_date",
            "payment_amount",
            "payment_method",
            "subtotal",
            "allowance_total",
            "discount_total",
            "grand_total",
            "description",
            "tags",
            "created",
            "last_updated",
        )
        default_columns = ("pk", "slug", "owner", "status", "due_date", "grand_total")


class InvoiceLineItemTable(ColdFrontTable):
    invoice = tables.Column(
        verbose_name=_("Invoice"),
        linkify=True,
    )
    line_type = columns.ChoiceFieldColumn(
        verbose_name=_("Line type"),
    )
    source_object = tables.Column(
        verbose_name=_("Source"),
        linkify=True,
        accessor=tables.A("source_object"),
        order_by=("source_object_type__model", "source_object_id"),
    )
    quantity = tables.Column(
        verbose_name=_("Quantity"),
        accessor=tables.A("quantity_display"),
    )
    unit_price = _money_column("unit_price", _("Unit price"))
    amount = _money_column("amount", _("Amount"))

    class Meta(ColdFrontTable.Meta):
        model = InvoiceLineItem
        fields = (
            "pk",
            "id",
            "invoice",
            "line_type",
            "source_object",
            "description",
            "quantity",
            "unit",
            "unit_price",
            "amount",
            "created",
            "last_updated",
        )
        default_columns = ("pk", "id", "invoice", "line_type", "source_object", "quantity", "unit", "amount")


class RateTable(PrimaryModelTable):
    name = tables.Column(
        verbose_name=_("Name"),
        linkify=True,
    )
    scope_object = tables.Column(
        verbose_name=_("Scope"),
        linkify=True,
        accessor=tables.A("scope_object"),
        order_by=("scope_object_type__model", "scope_object_id"),
    )
    unit = tables.Column(
        verbose_name=_("Unit"),
        accessor=tables.A("unit_display"),
    )
    amount = _money_column("amount", _("Amount"))
    charge_basis = columns.ChoiceFieldColumn(
        verbose_name=_("Charge basis"),
    )
    tags = columns.TagColumn(
        url_name="billing:rate_list",
    )

    class Meta(PrimaryModelTable.Meta):
        model = Rate
        fields = (
            "pk",
            "id",
            "name",
            "scope_object",
            "unit",
            "amount",
            "charge_basis",
            "effective_start",
            "effective_end",
            "description",
            "tags",
            "created",
            "last_updated",
        )
        default_columns = ("pk", "id", "name", "scope_object", "unit", "amount", "charge_basis")


class FreeAllowanceTable(PrimaryModelTable):
    name = tables.Column(
        verbose_name=_("Name"),
        linkify=True,
    )
    owner = tables.Column(
        verbose_name=_("Owner"),
    )
    scope_object = tables.Column(
        verbose_name=_("Scope"),
        linkify=True,
        accessor=tables.A("scope_object"),
        order_by=("scope_object_type__model", "scope_object_id"),
    )
    unit_format = tables.Column(
        verbose_name=_("Unit"),
    )
    quantity_total = tables.Column(
        verbose_name=_("Quantity"),
        accessor=tables.A("quantity_display"),
    )
    used = tables.Column(
        verbose_name=_("Used"),
        accessor=tables.A("used_display"),
    )
    remaining = tables.Column(
        verbose_name=_("Remaining"),
        accessor=tables.A("remaining_display"),
    )
    tags = columns.TagColumn(
        url_name="billing:freeallowance_list",
    )

    class Meta(PrimaryModelTable.Meta):
        model = FreeAllowance
        fields = (
            "pk",
            "id",
            "name",
            "owner",
            "scope_object",
            "unit_format",
            "quantity_total",
            "used",
            "remaining",
            "start_date",
            "end_date",
            "description",
            "tags",
            "created",
            "last_updated",
        )
        default_columns = (
            "pk",
            "id",
            "name",
            "owner",
            "scope_object",
            "unit_format",
            "quantity_total",
            "used",
        )


class DiscountTable(PrimaryModelTable):
    name = tables.Column(
        verbose_name=_("Name"),
        linkify=True,
    )
    owner = tables.Column(
        verbose_name=_("Owner"),
    )
    scope_object = tables.Column(
        verbose_name=_("Scope"),
        linkify=True,
        accessor=tables.A("scope_object"),
        order_by=("scope_object_type__model", "scope_object_id"),
    )
    type = columns.ChoiceFieldColumn(
        verbose_name=_("Type"),
    )
    tags = columns.TagColumn(
        url_name="billing:discount_list",
    )

    def render_owner(self, record):
        if record.owner:
            return str(record.owner)
        return _("(all users)")

    class Meta(PrimaryModelTable.Meta):
        model = Discount
        fields = (
            "pk",
            "id",
            "name",
            "owner",
            "scope_object",
            "type",
            "value",
            "description",
            "tags",
            "created",
            "last_updated",
        )
        default_columns = ("pk", "id", "name", "owner", "scope_object", "type", "value", "description")
