# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.utils.translation import gettext_lazy as _

from coldfront.choices import ChoiceSet


class InvoiceStatusChoices(ChoiceSet):
    """Lifecycle statuses for an Invoice."""

    STATUS_DRAFT = "draft"
    STATUS_INVOICED = "invoiced"
    STATUS_PAID = "paid"
    STATUS_VOID = "void"

    CHOICES = [
        (STATUS_DRAFT, _("Draft"), "secondary"),
        (STATUS_INVOICED, _("Invoiced"), "primary"),
        (STATUS_PAID, _("Paid"), "success"),
        (STATUS_VOID, _("Void"), "danger"),
    ]


class InvoiceLineTypeChoices(ChoiceSet):
    """The kind of amount represented by an invoice line item."""

    TYPE_CHARGE = "charge"
    TYPE_FREE_ALLOWANCE = "free_allowance"
    TYPE_DISCOUNT = "discount"
    TYPE_CREDIT = "credit"

    CHOICES = [
        (TYPE_CHARGE, _("Charge"), "primary"),
        (TYPE_FREE_ALLOWANCE, _("Free allowance"), "info"),
        (TYPE_DISCOUNT, _("Discount"), "success"),
        (TYPE_CREDIT, _("Credit"), "success"),
    ]


class ChargeBasisChoices(ChoiceSet):
    """The cadence at which a Rate recurs."""

    BASIS_ONE_TIME = "one_time"
    BASIS_MONTHLY = "monthly"
    BASIS_YEARLY = "yearly"

    CHOICES = [
        (BASIS_ONE_TIME, _("One time")),
        (BASIS_MONTHLY, _("Monthly")),
        (BASIS_YEARLY, _("Yearly")),
    ]


class DiscountTypeChoices(ChoiceSet):
    """How a Discount reduces an invoice total."""

    TYPE_PERCENTAGE = "percentage"
    TYPE_FLAT = "flat"
    TYPE_NO_COST = "no_cost"

    CHOICES = [
        (TYPE_PERCENTAGE, _("Percentage")),
        (TYPE_FLAT, _("Flat")),
        (TYPE_NO_COST, _("No cost")),
    ]


class PaymentMethodChoices(ChoiceSet):
    """Accepted payment methods recorded on an Invoice."""

    METHOD_WIRE = "wire"
    METHOD_CHECK = "check"
    METHOD_PO = "po"
    METHOD_INTERNAL = "internal"

    CHOICES = [
        (METHOD_WIRE, _("Wire transfer")),
        (METHOD_CHECK, _("Check")),
        (METHOD_PO, _("Purchase order")),
        (METHOD_INTERNAL, _("Internal transfer")),
    ]


class UnitFormatChoiceSet(ChoiceSet):
    """The native dimensions used to express quantities and prices.

    Values are dimensions, not display labels: the human-readable unit (e.g.
    "1.0 TB") is derived from the native divisor via ``humanize``. The ``key``
    allows centers to replace/extend the catalog via the FIELD_CHOICES
    configuration parameter, following ColdFront conventions.
    """

    key = "billing.units"

    UNIT_BYTES = "bytes"
    UNIT_SERVICE_UNITS = "service_units"
    UNIT_CORE_HOURS = "core_hours"
    UNIT_PER_ITEM = "per_item"

    CHOICES = [
        (UNIT_BYTES, _("Bytes")),
        (UNIT_SERVICE_UNITS, _("Service Units")),
        (UNIT_CORE_HOURS, _("Core Hours")),
        (UNIT_PER_ITEM, _("Flat / per-item")),
    ]
