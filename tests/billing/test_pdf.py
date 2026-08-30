# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import pytest
from django.test import RequestFactory
from djmoney.money import Money

from coldfront.billing.choices import InvoiceLineTypeChoices, InvoiceStatusChoices
from coldfront.billing.models import Invoice, InvoiceLineItem
from coldfront.billing.pdf import render_invoice_pdf
from coldfront.users.models import User


def _invoice(owner):
    return Invoice.objects.create(slug="INV-1", owner=owner, status=InvoiceStatusChoices.STATUS_INVOICED)


def _request(owner):
    request = RequestFactory().get("/")
    # Context processors (e.g. unread_notifications_count) need request.user.
    request.user = owner
    return request


@pytest.mark.django_db
def test_render_invoice_pdf_smoke():
    owner = User.objects.create_user(username="pi")
    invoice = _invoice(owner)
    InvoiceLineItem.objects.create(
        invoice=invoice,
        line_type=InvoiceLineTypeChoices.TYPE_CHARGE,
        description="Compute time",
        quantity=1,
        unit="1.0",
        unit_price=Money("10.00", "USD"),
        amount=Money("10.00", "USD"),
    )
    invoice.subtotal = Money("10.00", "USD")
    invoice.grand_total = Money("10.00", "USD")
    invoice.save()

    data = render_invoice_pdf(invoice, _request(owner))

    assert data.startswith(b"%PDF")
    assert len(data) > 100
