# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime

from django.utils.translation import gettext_lazy as _
from fpdf import FPDF

from coldfront.billing.choices import InvoiceStatusChoices

__all__ = ("render_invoice_pdf",)


def _money(value):
    """Render a django-money value as '<amount> <code>', or '-' when unset."""
    if value is None:
        return "-"
    return f"{value.amount:,.2f} {value.currency.code}"


def _date(value):
    if value is None:
        return "-"
    return value.strftime("%Y-%m-%d") if isinstance(value, datetime) else str(value)


def render_invoice_pdf(invoice):
    """
    Render a simple A4 invoice PDF with the line items and totals for ``invoice``.
    Returns the raw PDF bytes. A fresh ``FPDF`` instance is created per call so
    the document can be reused across requests.
    """
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # ---- Header -----------------------------------------------------------
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, f"Invoice {invoice.slug}", align="C")
    pdf.ln(12)

    # ---- Billing info -----------------------------------------------------
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 6, f"Owner: {invoice.owner}", align="L")
    pdf.ln(6)
    pdf.cell(0, 6, f"Status: {invoice.get_status_display()}", align="L")
    pdf.ln(6)
    pdf.cell(0, 6, f"Period: {_date(invoice.start_date)} - {_date(invoice.end_date)}", align="L")
    pdf.ln(6)
    pdf.cell(0, 6, f"Due date: {_date(invoice.due_date)}", align="L")
    pdf.ln(6)

    projects = ", ".join(p.name for p in invoice.projects.all()) or _("All projects")
    pdf.cell(0, 6, f"Projects: {projects}", align="L")
    pdf.ln(10)

    # ---- Line items -------------------------------------------------------
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, _("Line items"), align="L")
    pdf.ln(8)

    line_items = list(invoice.line_items.order_by("line_type", "id"))
    if line_items:
        with pdf.table(first_row_as_headings=True, col_widths=(60, 24, 20, 22, 24, 28)) as table:
            table.row(
                [
                    _("Description"),
                    _("Type"),
                    _("Quantity"),
                    _("Unit"),
                    _("Unit price"),
                    _("Amount"),
                ]
            )
            for item in line_items:
                table.row(
                    [
                        item.description or "-",
                        item.get_line_type_display(),
                        item.quantity_display or "-",
                        item.unit or "-",
                        _money(item.unit_price),
                        _money(item.amount),
                    ]
                )
    else:
        pdf.set_font("Helvetica", size=10)
        pdf.cell(0, 6, _("No line items."), align="L")
    pdf.ln(10)

    # ---- Totals -----------------------------------------------------------
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, _("Totals"), align="L")
    pdf.ln(8)

    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 6, f"{_('Subtotal')}: {_money(invoice.subtotal)}", align="L")
    pdf.ln(6)
    pdf.cell(0, 6, f"{_('Allowance total')}: {_money(invoice.allowance_total)}", align="L")
    pdf.ln(6)
    pdf.cell(0, 6, f"{_('Discount total')}: {_money(invoice.discount_total)}", align="L")
    pdf.ln(8)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, f"{_('Grand total')}: {_money(invoice.grand_total)}", align="L")
    pdf.ln(10)

    # ---- Payment ----------------------------------------------------------
    if invoice.status == InvoiceStatusChoices.STATUS_PAID:
        pdf.set_font("Helvetica", size=10)
        pdf.cell(0, 6, f"{_('Payment date')}: {_date(invoice.payment_date)}", align="L")
        pdf.ln(6)
        pdf.cell(0, 6, f"{_('Payment amount')}: {_money(invoice.payment_amount)}", align="L")
        pdf.ln(6)
        pdf.cell(0, 6, f"{_('Payment method')}: {invoice.payment_method or '-'}", align="L")

    # ---- Footer page numbers ----------------------------------------------
    pdf.set_y(-15)
    pdf.set_font("Helvetica", size=8)
    pdf.cell(0, 10, f"Page {pdf.page_no()}/{{nb}}", align="C")

    return bytes(pdf.output())
