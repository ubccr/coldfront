# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from decimal import ROUND_HALF_EVEN, Decimal

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from djmoney.money import Money

from coldfront.billing.choices import (
    DiscountTypeChoices,
    InvoiceLineTypeChoices,
    InvoiceStatusChoices,
)
from coldfront.billing.models import Discount, FreeAllowance, Invoice, InvoiceLineItem, Rate
from coldfront.models.utils import get_default_currency
from coldfront.registry import get_billing_sources

__all__ = ("BillingConfigurationError", "finalize_invoice", "generate_invoice")

DEFAULT_CURRENCY = get_default_currency()


class BillingConfigurationError(Exception):
    """A registered billing source is misconfigured and cannot be billed."""


def _round2(value):
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


def _in_period(obj_start, obj_end, invoice_start, invoice_end):
    """True if [obj_start, obj_end] overlaps the invoice period (null = open)."""
    if invoice_start is None and invoice_end is None:
        return True
    if obj_start and invoice_end and obj_start > invoice_end:
        return False
    if obj_end and invoice_start and obj_end < invoice_start:
        return False
    return True


def _resolve_rate(scope):
    ct = ContentType.objects.get_for_model(scope)
    return Rate.objects.filter(scope_object_type=ct, scope_object_id=scope.pk).first()


def _already_billed(source, invoice):
    """True if the source already has a charge line in an invoiced (non-voided)
    invoice whose period overlaps this invoice's period."""
    ct = ContentType.objects.get_for_model(source)
    qs = InvoiceLineItem.objects.filter(
        line_type=InvoiceLineTypeChoices.TYPE_CHARGE,
        source_object_type=ct,
        source_object_id=source.pk,
        invoice__status__in=[
            InvoiceStatusChoices.STATUS_INVOICED,
            InvoiceStatusChoices.STATUS_PAID,
        ],
    )
    if invoice.start_date is None and invoice.end_date is None:
        return qs.exists()
    overlap = Q(
        Q(invoice__start_date__isnull=True) | Q(invoice__start_date__lte=invoice.end_date),
        Q(invoice__end_date__isnull=True) | Q(invoice__end_date__gte=invoice.start_date),
    )
    return qs.filter(overlap).exists()


def _allowance_matches(allowance, charge):
    """
    An allowance matches a charge on unit_format and scope. Allowances are
    always scoped to a single resource (scope is required on the model), so a
    global (scope-less) allowance is never valid.
    """
    if allowance.unit_format != charge["unit_format"]:
        return False
    if not allowance.scope_object_type_id:
        raise BillingConfigurationError(
            _("Free allowance {pk} has no scope — allowances must be scoped to a resource.").format(pk=allowance.pk)
        )
    ct = ContentType.objects.get_for_model(charge["scope"])
    if allowance.scope_object_type_id != ct.pk or allowance.scope_object_id != charge["scope"].pk:
        return False
    return True


def _matching_allowances(invoice, unit_format):
    return FreeAllowance.objects.filter(owner=invoice.owner, unit_format=unit_format)


def generate_invoice(invoice):
    """
    (Re)build the line items and totals for a draft invoice. Idempotent: deletes
    and recreates charge/free-allowance/discount lines, leaving manual credit
    lines untouched. Never consumes allowance pools (finalize does that once).
    """
    selected_cts = set(invoice.source_types.values_list("pk", flat=True))
    default_currency = DEFAULT_CURRENCY

    # ---- Pass A: charges ---------------------------------------------------
    charges = []
    for src in get_billing_sources():
        if selected_cts:
            ct = ContentType.objects.get_for_model(src["model"])
            if ct.pk not in selected_cts:
                continue
        for instance in src["get_billable"](invoice.owner):
            if _already_billed(instance, invoice):
                continue
            scope = src["get_rate_scope"](instance)
            if not isinstance(scope, src["scope"]):
                raise BillingConfigurationError(
                    "Billing source {model} registered with scope {scope} "
                    "but get_rate_scope returned {actual} ({actual_type}) — "
                    "please fix the registration config.".format(
                        model=src["model"]._meta.label_lower,
                        scope=src["scope"]._meta.label_lower,
                        actual=scope,
                        actual_type=scope.__class__._meta.label_lower if scope else "None",
                    )
                )
            qty = src["get_quantity"](instance, invoice)
            if qty == 0:
                continue
            rate = _resolve_rate(scope) if scope is not None else None
            if rate is not None and not _in_period(
                rate.effective_start, rate.effective_end, invoice.start_date, invoice.end_date
            ):
                rate = None
            if rate is None:
                continue  # no rate -> the admin chooses not to bill
            if str(rate.amount.currency) != str(default_currency):
                continue  # v1: single currency, no conversion
            if qty is None:
                charges.append(
                    {
                        "scope": scope,
                        "source": instance,
                        "qty": None,
                        "rate": None,
                        "is_valid": False,
                        "description": _("Needs fixing: quantity not set"),
                    }
                )
                continue
            billed = Decimal(qty) / Decimal(rate.unit)
            amount = _round2(billed * Decimal(rate.amount.amount))
            charges.append(
                {
                    "scope": scope,
                    "source": instance,
                    "qty": qty,
                    "rate": rate,
                    "billed": billed,
                    "amount": amount,
                    "unit_format": rate.unit_format,
                    "is_valid": True,
                    "description": f"{scope} - {instance}",
                }
            )

    # ---- Pass B: free allowances (stacking) --------------------------------
    free_lines = []
    valid_charges = [c for c in charges if c["is_valid"]]
    # Group by unit_format; deterministic order: source
    for unit_format in {c["unit_format"] for c in valid_charges}:
        group = [c for c in valid_charges if c["unit_format"] == unit_format]
        allowances = _matching_allowances(invoice, unit_format)
        # Track native units drawn from each allowance pool across charges so a
        # shared pool is capped at its remaining amount (e.g. one cluster-scoped
        # allowance covering several accounts). ``allowance.remaining`` is the
        # model property (quantity_total - used); generation never persists
        # ``used`` (finalize does), so consume in-memory per allowance here.
        allowance_consumed = {}
        for charge in group:
            remaining = charge["billed"]
            for allowance in allowances:
                if not _allowance_matches(allowance, charge):
                    continue
                if remaining <= 0:
                    break
                pool_remaining = Decimal(allowance.remaining) - Decimal(allowance_consumed.get(allowance.pk, 0))
                if pool_remaining <= 0:
                    continue
                coverage = min(remaining, pool_remaining / Decimal(charge["rate"].unit))
                if coverage > 0:
                    native = coverage * Decimal(charge["rate"].unit)
                    allowance_consumed[allowance.pk] = allowance_consumed.get(allowance.pk, 0) + int(native)
                    free_lines.append(
                        {
                            "source": allowance,
                            "charge": charge,
                            "quantity": int(native),
                            "unit": charge["rate"].unit_display,
                            "unit_format": charge["rate"].unit_format,
                            "amount": -_round2(coverage * Decimal(charge["rate"].amount.amount)),
                            "description": allowance.name,
                        }
                    )
                    remaining -= coverage

    # ---- Pass C: discount (single per charge, not double-applied) ----------
    # Discount applies to the net per resource scope (plus the leftover user
    # net), i.e. charge subtotal plus free allowances, never below zero (capped
    # at net). Precedence: owner+resource > resource > owner > global.
    discount_lines = []
    net_by_scope = {}
    user_net = Decimal("0")
    for charge in valid_charges:
        user_net += charge["amount"]
        net_by_scope[charge["scope"]] = net_by_scope.get(charge["scope"], Decimal("0")) + charge["amount"]
    for line in free_lines:
        user_net += line["amount"]
        scope = line["charge"]["scope"]
        net_by_scope[scope] = net_by_scope.get(scope, Decimal("0")) + line["amount"]

    consumed = set()
    for scope, net in net_by_scope.items():
        ct = ContentType.objects.get_for_model(scope)
        discount = (
            Discount.objects.filter(owner=invoice.owner, scope_object_type=ct, scope_object_id=scope.pk)
            .order_by("created")
            .first()
        )
        if discount is None:
            discount = (
                Discount.objects.filter(owner__isnull=True, scope_object_type=ct, scope_object_id=scope.pk)
                .order_by("created")
                .first()
            )
        if discount is not None:
            value = _discount_value(discount, net)
            discount_lines.append(
                {
                    "source": discount,
                    "scope": scope,
                    "amount": -value,
                    "description": discount.name,
                }
            )
            consumed.add(scope)

    leftover = user_net - sum((net_by_scope[s] for s in consumed), Decimal("0"))
    user_discount = (
        Discount.objects.filter(owner=invoice.owner, scope_object_id__isnull=True).order_by("created").first()
    )
    if user_discount is None:
        user_discount = (
            Discount.objects.filter(owner__isnull=True, scope_object_id__isnull=True).order_by("created").first()
        )
    if user_discount is not None and leftover > 0:
        value = _discount_value(user_discount, leftover)
        discount_lines.append(
            {
                "source": user_discount,
                "amount": -value,
                "description": _("Discount ({type})").format(type=user_discount.type),
            }
        )

    # ---- Totals ------------------------------------------------------------
    subtotal = sum((c["amount"] for c in valid_charges), Decimal("0"))
    allowance_total = sum((line["amount"] for line in free_lines), Decimal("0"))
    net = subtotal + allowance_total
    discount_total = sum((line["amount"] for line in discount_lines), Decimal("0"))
    grand_total = net + discount_total

    # ---- Persist -----------------------------------------------------------
    # Use a queryset update (not ``invoice.save()``) so the totals are written
    # without triggering the change-logging middleware: when an invoice is
    # created and generated in one step, the totals are part of the creation
    # rather than a second "modify" change.
    Invoice.objects.filter(pk=invoice.pk).update(
        subtotal=Money(subtotal, default_currency),
        allowance_total=Money(allowance_total, default_currency),
        discount_total=Money(discount_total, default_currency),
        grand_total=Money(grand_total, default_currency),
    )
    invoice.refresh_from_db()

    # Rebuild only generated line types; keep manual credit lines
    InvoiceLineItem.objects.filter(
        invoice=invoice,
        line_type__in=[
            InvoiceLineTypeChoices.TYPE_CHARGE,
            InvoiceLineTypeChoices.TYPE_FREE_ALLOWANCE,
            InvoiceLineTypeChoices.TYPE_DISCOUNT,
        ],
    ).delete()

    for c in charges:
        InvoiceLineItem.objects.create(
            invoice=invoice,
            line_type=InvoiceLineTypeChoices.TYPE_CHARGE,
            source_object=c["source"],
            description=c["description"],
            is_valid=c["is_valid"],
            quantity=c.get("qty"),
            unit=c["rate"].unit_display if c["rate"] else "",
            unit_format=c["rate"].unit_format if c["rate"] else "",
            unit_price=c["rate"].amount if c["rate"] else None,
            amount=Money(c["amount"], default_currency) if c["is_valid"] else None,
        )
    for line in free_lines:
        InvoiceLineItem.objects.create(
            invoice=invoice,
            line_type=InvoiceLineTypeChoices.TYPE_FREE_ALLOWANCE,
            source_object=line["source"],
            description=line["description"],
            is_valid=True,
            quantity=line["quantity"],
            unit=line["unit"],
            unit_format=line["unit_format"],
            amount=Money(line["amount"], default_currency),
        )
    for line in discount_lines:
        InvoiceLineItem.objects.create(
            invoice=invoice,
            line_type=InvoiceLineTypeChoices.TYPE_DISCOUNT,
            source_object=line["source"],
            description=line["description"],
            is_valid=True,
            amount=Money(line["amount"], default_currency),
        )


def _discount_value(discount, net):
    """Compute the discount value against ``net`` (capped at net)."""
    if net <= 0:
        return Decimal("0")
    if discount.type == DiscountTypeChoices.TYPE_PERCENTAGE:
        value = net * (Decimal(discount.value or 0) / Decimal("100"))
    elif discount.type == DiscountTypeChoices.TYPE_NO_COST:
        value = net
    else:  # flat
        value = min(Decimal(discount.value or 0), net)
    return _round2(value)


def finalize_invoice(invoice):
    """
    Lock a draft invoice: consume free-allowance pools once and drop any
    invalid (un-priced) line items. Raises if the invoice has no valid charge
    lines, so a zero/invalid-only invoice cannot be finalized.

    Called by the finalize transition; does not change the status itself.
    """
    valid_charges = invoice.line_items.filter(line_type=InvoiceLineTypeChoices.TYPE_CHARGE, is_valid=True)
    if not valid_charges.exists():
        raise ValueError(_("This invoice has no valid line items; fix invalid lines or generate first."))

    # Consume free-allowance pools once, from the generated free-allowance lines
    fa_lines = invoice.line_items.filter(line_type=InvoiceLineTypeChoices.TYPE_FREE_ALLOWANCE, is_valid=True)
    for allowance_pk in fa_lines.values_list("source_object_id", flat=True).distinct():
        native = sum(fa_lines.filter(source_object_id=allowance_pk).values_list("quantity", flat=True))
        allowance = FreeAllowance.objects.get(pk=allowance_pk)
        allowance.used = min(allowance.quantity_total, allowance.used + native)
        allowance.save()

    # Drop invalid (un-priced) lines so the locked invoice is clean
    invoice.line_items.filter(is_valid=False).delete()
