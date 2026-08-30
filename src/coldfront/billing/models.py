# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import humanize
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from djmoney.models.fields import MoneyField

from coldfront.billing.choices import (
    ChargeBasisChoices,
    DiscountTypeChoices,
    InvoiceLineTypeChoices,
    InvoiceStatusChoices,
    PaymentMethodChoices,
    UnitFormatChoiceSet,
)
from coldfront.models import ChangeLoggedModel, PrimaryModel
from coldfront.models.features import CommentingMixin
from coldfront.models.fields import AutoSlugField
from coldfront.models.utils import get_currency_choices, get_default_currency

__all__ = (
    "Discount",
    "FreeAllowance",
    "Invoice",
    "InvoiceLineItem",
    "Rate",
)


def _unit_display(unit_format, unit):
    """Render a native ``unit`` (divisor) against its ``unit_format`` dimension.

    ``bytes`` is humanized (e.g. 1e12 -> "1.0 TB"); ``1`` is the flat per-item
    quantum; any other dimension (e.g. ``SU``) is shown as-is.
    """
    if unit_format == UnitFormatChoiceSet.UNIT_BYTES:
        return humanize.naturalsize(unit)
    if unit_format == UnitFormatChoiceSet.UNIT_PER_ITEM:
        return "1"
    return unit_format


def _quantity_display(unit_format, value):
    """Render a free-allowance quantity (total, used, or remaining) for display.

    Byte quantities are humanized (e.g. 1e12 -> "1.0 TB"); anything else is
    shown as the plain integer followed by its ``unit_format`` label.
    """
    if unit_format == UnitFormatChoiceSet.UNIT_BYTES:
        return humanize.naturalsize(value)
    return f"{value} {unit_format}"


class Invoice(CommentingMixin, PrimaryModel):
    """
    A bill sent to a responsible user (owner) for a billing period, optionally
    restricted to specific registered billing source types (``source_types``).

    The owner is the party responsible for paying the bill; all of the owner's
    billable sources are considered unless ``source_types`` restricts them.
    """

    slug = AutoSlugField(
        verbose_name=_("slug"),
    )

    source_types = models.ManyToManyField(
        to="contenttypes.ContentType",
        blank=True,
        related_name="billing_invoices",
        verbose_name=_("source types"),
        help_text=_("Restrict the invoice to specific registered billing source types. Leave empty to bill all."),
    )

    owner = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_invoices",
        null=False,
        verbose_name=_("owner"),
        help_text=_("The user responsible for paying this invoice."),
    )

    start_date = models.DateTimeField(
        verbose_name=_("start date"),
        blank=True,
        null=True,
    )
    end_date = models.DateTimeField(
        verbose_name=_("end date"),
        blank=True,
        null=True,
    )
    due_date = models.DateTimeField(
        verbose_name=_("due date"),
        blank=True,
        null=True,
    )

    status = models.CharField(
        verbose_name=_("status"),
        max_length=50,
        choices=InvoiceStatusChoices,
        default=InvoiceStatusChoices.STATUS_DRAFT,
    )

    # Payment data recorded when the invoice is paid.
    payment_date = models.DateTimeField(
        verbose_name=_("payment date"),
        blank=True,
        null=True,
    )
    payment_amount = MoneyField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        currency_choices=get_currency_choices,
        default_currency=get_default_currency,
        verbose_name=_("payment amount"),
    )
    payment_method = models.CharField(
        verbose_name=_("payment method"),
        max_length=50,
        choices=PaymentMethodChoices,
        blank=True,
    )

    # Computed totals (all MoneyField, single currency).
    subtotal = MoneyField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        currency_choices=get_currency_choices,
        default_currency=get_default_currency,
        verbose_name=_("subtotal"),
    )
    allowance_total = MoneyField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        currency_choices=get_currency_choices,
        default_currency=get_default_currency,
        verbose_name=_("allowance total"),
    )
    discount_total = MoneyField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        currency_choices=get_currency_choices,
        default_currency=get_default_currency,
        verbose_name=_("discount total"),
    )
    grand_total = MoneyField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        currency_choices=get_currency_choices,
        default_currency=get_default_currency,
        verbose_name=_("grand total"),
    )

    clone_fields = (
        "description",
        "status",
    )

    prerequisite_models = ("billing.Rate",)

    class Meta:
        ordering = ["created"]
        verbose_name = _("invoice")
        verbose_name_plural = _("invoices")
        permissions = (
            ("generate_invoice", _("Generate invoice")),
            ("finalize_invoice", _("Finalize invoice")),
            ("pay_invoice", _("Pay invoice")),
            ("void_invoice", _("Void invoice")),
        )

    def __str__(self):
        return self.slug

    def get_status_color(self):
        return InvoiceStatusChoices.colors.get(self.status)

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("billing:invoice", args=[self.pk])

    @property
    def is_overdue(self):
        """Derived overdue flag: invoiced and past the due date."""
        from django.utils import timezone

        if self.status != InvoiceStatusChoices.STATUS_INVOICED or not self.due_date:
            return False
        return self.due_date < timezone.now()


class InvoiceLineItem(ChangeLoggedModel):
    """
    A single row on an Invoice. Charge lines carry the amount for a billing
    source; free-allowance, discount, and credit lines carry negative amounts.

    The ``source`` is a GenericForeignKey to the billing source (e.g. a
    ``StorageQuota`` or ``SlurmAccount``), wired up in later phases.
    """

    invoice = models.ForeignKey(
        to="billing.Invoice",
        on_delete=models.CASCADE,
        related_name="line_items",
        verbose_name=_("invoice"),
    )

    line_type = models.CharField(
        verbose_name=_("line type"),
        max_length=50,
        choices=InvoiceLineTypeChoices,
        default=InvoiceLineTypeChoices.TYPE_CHARGE,
    )

    source_object_type = models.ForeignKey(
        to="contenttypes.ContentType",
        on_delete=models.PROTECT,
        related_name="billing_line_items",
        blank=True,
        null=True,
        verbose_name=_("source type"),
    )
    source_object_id = models.PositiveBigIntegerField(
        blank=True,
        null=True,
        verbose_name=_("source object"),
    )
    source_object = GenericForeignKey(
        ct_field="source_object_type",
        fk_field="source_object_id",
    )

    is_valid = models.BooleanField(
        verbose_name=_("valid"),
        default=True,
        help_text=_("False if the line could not be priced at generation time and needs fixing."),
    )

    description = models.CharField(
        verbose_name=_("description"),
        max_length=200,
        blank=True,
    )

    quantity = models.PositiveBigIntegerField(
        blank=True,
        null=True,
        verbose_name=_("quantity"),
        help_text=_("Quantity in the source's native units (e.g. bytes)."),
    )

    unit = models.CharField(
        verbose_name=_("unit"),
        max_length=50,
        blank=True,
        help_text=_("Snapshot of the human-readable unit label at generation time (e.g. '1.0 TB')."),
    )

    unit_format = models.CharField(
        verbose_name=_("unit format"),
        max_length=50,
        choices=UnitFormatChoiceSet,
        blank=True,
        help_text=_("Snapshot of the native unit dimension at generation time"),
    )

    unit_price = MoneyField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        currency_choices=get_currency_choices,
        default_currency=get_default_currency,
        verbose_name=_("unit price"),
    )

    amount = MoneyField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        currency_choices=get_currency_choices,
        default_currency=get_default_currency,
        verbose_name=_("amount"),
    )

    class Meta:
        ordering = ["invoice", "id"]
        verbose_name = _("invoice line item")
        verbose_name_plural = _("invoice line items")

    def __str__(self):
        return f"{self.invoice} line {self.pk} ({self.line_type})"

    def get_status_color(self):
        return InvoiceLineTypeChoices.colors.get(self.line_type)

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("billing:invoicelineitem", args=[self.pk])

    @property
    def quantity_display(self):
        """Render the line item quantity, humanizing byte quantities."""
        if self.quantity is None:
            return ""
        if self.unit_format == UnitFormatChoiceSet.UNIT_BYTES:
            return humanize.naturalsize(self.quantity)
        return str(self.quantity)


class Rate(PrimaryModel):
    """
    A per-unit price scoped to a resource (StorageResource, SlurmCluster, or
    SlurmQOS). ``charge_basis`` describes the billing cadence.
    """

    name = models.CharField(
        verbose_name=_("name"),
        max_length=100,
        unique=True,
        default="",
    )

    scope_object_type = models.ForeignKey(
        to="contenttypes.ContentType",
        on_delete=models.PROTECT,
        related_name="billing_rates",
        verbose_name=_("scope type"),
    )
    scope_object_id = models.PositiveBigIntegerField(
        verbose_name=_("scope object"),
    )
    scope_object = GenericForeignKey(
        ct_field="scope_object_type",
        fk_field="scope_object_id",
    )

    unit = models.PositiveBigIntegerField(
        verbose_name=_("unit"),
        validators=[MinValueValidator(1)],
        help_text=_("Native units per billed unit (the divisor). e.g. 1.0 TB for per-TB pricing."),
    )

    unit_format = models.CharField(
        verbose_name=_("unit format"),
        max_length=50,
        choices=UnitFormatChoiceSet,
        help_text=_("The native unit dimension this rate prices"),
    )

    amount = MoneyField(
        max_digits=14,
        decimal_places=2,
        currency_choices=get_currency_choices,
        default_currency=get_default_currency,
        verbose_name=_("amount"),
        help_text=_("Price per billing unit."),
    )

    charge_basis = models.CharField(
        verbose_name=_("charge basis"),
        max_length=50,
        choices=ChargeBasisChoices,
        default=ChargeBasisChoices.BASIS_ONE_TIME,
    )

    effective_start = models.DateTimeField(
        verbose_name=_("effective start"),
        blank=True,
        null=True,
    )
    effective_end = models.DateTimeField(
        verbose_name=_("effective end"),
        blank=True,
        null=True,
    )

    clone_fields = (
        "description",
        "unit",
        "unit_format",
        "amount",
        "charge_basis",
    )

    class Meta:
        ordering = ["created"]
        verbose_name = _("rate")
        verbose_name_plural = _("rates")
        constraints = [
            models.UniqueConstraint(
                fields=("scope_object_type", "scope_object_id"),
                name="billing_rate_unique_scope",
            ),
            models.CheckConstraint(condition=models.Q(unit__gt=0), name="billing_rate_unit_positive"),
        ]

    def __str__(self):
        return self.name

    @property
    def unit_display(self):
        return _unit_display(self.unit_format, self.unit)

    def get_status_color(self):
        return "green"


class FreeAllowance(PrimaryModel):
    """
    A pool of free units granted to a user (owner) and scoped to a single
    resource (scope is required). ``used`` tracks consumption so the pool is
    drawn down over the allowance period.
    """

    name = models.CharField(
        verbose_name=_("name"),
        max_length=100,
        unique=True,
        default="",
    )

    owner = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="free_allowances",
        null=False,
        verbose_name=_("owner"),
        help_text=_("The user granted this free allowance."),
    )

    scope_object_type = models.ForeignKey(
        to="contenttypes.ContentType",
        on_delete=models.PROTECT,
        related_name="billing_free_allowances",
        verbose_name=_("scope type"),
    )
    scope_object_id = models.PositiveBigIntegerField(
        verbose_name=_("scope object"),
    )
    scope_object = GenericForeignKey(
        ct_field="scope_object_type",
        fk_field="scope_object_id",
    )

    unit_format = models.CharField(
        verbose_name=_("unit format"),
        max_length=50,
        choices=UnitFormatChoiceSet,
        default=UnitFormatChoiceSet.UNIT_PER_ITEM,
        help_text=_("The native unit dimension of the allowance"),
    )

    quantity_total = models.PositiveBigIntegerField(
        verbose_name=_("total quantity"),
        help_text=_("Total free units granted, in native units (e.g. bytes)."),
    )

    used = models.PositiveBigIntegerField(
        verbose_name=_("used"),
        default=0,
        help_text=_("Free units already consumed against invoices."),
    )

    start_date = models.DateTimeField(
        verbose_name=_("start date"),
        blank=True,
        null=True,
    )
    end_date = models.DateTimeField(
        verbose_name=_("end date"),
        blank=True,
        null=True,
    )

    clone_fields = ("quantity_total",)

    class Meta:
        ordering = ["created"]
        verbose_name = _("free allowance")
        verbose_name_plural = _("free allowances")

    def __str__(self):
        return self.name

    def get_status_color(self):
        return "green"

    @property
    def quantity_display(self):
        return _quantity_display(self.unit_format, self.quantity_total)

    @property
    def used_display(self):
        return _quantity_display(self.unit_format, self.used)

    @property
    def remaining_display(self):
        return _quantity_display(self.unit_format, self.remaining)

    @property
    def remaining(self):
        return max(self.quantity_total - self.used, 0)


class Discount(PrimaryModel):
    """
    A reduction applied to an invoice net total. A discount may be scoped by
    owner (a user), by resource (``scope_object``), or both, or neither:

    - owner + resource: a specific user gets a discount on a specific resource.
    - resource only: all users get a discount on a specific resource.
    - owner only: a specific user gets a discount on all resources.
    - neither (global): everyone gets a discount on everything (e.g. a No Cost
      discount that zeroes invoices while still showing the underlying charges).

    Precedence for a given charge is owner+resource > resource > owner > global;
    discounts are never stacked.
    """

    name = models.CharField(
        verbose_name=_("name"),
        max_length=100,
        unique=True,
        default="",
    )

    owner = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="discounts",
        blank=True,
        null=True,
        verbose_name=_("owner"),
        help_text=_("The user this discount applies to. Leave empty for a global or resource-scoped discount."),
    )

    scope_object_type = models.ForeignKey(
        to="contenttypes.ContentType",
        on_delete=models.PROTECT,
        related_name="billing_discounts",
        blank=True,
        null=True,
        verbose_name=_("scope type"),
    )
    scope_object_id = models.PositiveBigIntegerField(
        blank=True,
        null=True,
        verbose_name=_("scope object"),
    )
    scope_object = GenericForeignKey(
        ct_field="scope_object_type",
        fk_field="scope_object_id",
    )

    type = models.CharField(
        verbose_name=_("type"),
        max_length=50,
        choices=DiscountTypeChoices,
        default=DiscountTypeChoices.TYPE_PERCENTAGE,
    )

    value = models.DecimalField(
        verbose_name=_("value"),
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text=_("Percentage (0-100) or flat amount depending on the type."),
    )

    clone_fields = ("type", "value")

    class Meta:
        ordering = ["created"]
        verbose_name = _("discount")
        verbose_name_plural = _("discounts")

    def __str__(self):
        return self.name

    def get_status_color(self):
        return "green"
