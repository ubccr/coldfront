# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.template.loader import render_to_string
from fpdf import FPDF

from coldfront.billing.choices import InvoiceStatusChoices

__all__ = ("render_invoice_pdf",)

PDF_TEMPLATE = "billing/pdf_invoice.html"


class _InvoicePDF(FPDF):
    """A4 PDF whose ``footer()`` draws a centered page number on every page."""

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", size=8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


def _pdf_context(invoice):
    """Curated context for the invoice PDF template."""
    return {
        "invoice": invoice,
        # Preserve the deterministic line-item ordering used by the old PDF.
        "line_items": invoice.line_items.order_by("line_type", "id"),
        "status_paid": InvoiceStatusChoices.STATUS_PAID,
    }


def render_invoice_pdf(invoice, request):
    """
    Render the invoice as an A4 PDF from the ``billing/pdf_invoice.html``
    template. Returns the raw PDF bytes. A fresh ``FPDF`` instance is created
    per call so the document can be reused across requests.

    ``request`` enables the RequestContext: the ``{{ settings }}`` context
    processor (for center info) and request-language ``{% trans %}`` both work.
    """
    pdf = _InvoicePDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    html = render_to_string(PDF_TEMPLATE, _pdf_context(invoice), request=request)
    pdf.write_html(
        html,
        font_family="Helvetica",
    )

    if invoice.status == InvoiceStatusChoices.STATUS_DRAFT:
        # add draft watermark
        with pdf.local_context(fill_opacity=0.25):
            pdf.set_font("Helvetica", style="B", size=210)
            pdf.set_text_color(200, 200, 200)
            center_x = 105
            center_y = 148.5
            text_string = "DRAFT"
            text_width = pdf.get_string_width(text_string)
            start_x = center_x - (text_width / 2)
            start_y = center_y + (pdf.font_size / 3)
            with pdf.rotation(angle=54.74, x=center_x, y=center_y):
                pdf.text(start_x, start_y, text_string)

    return bytes(pdf.output())
