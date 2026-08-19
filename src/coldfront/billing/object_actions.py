# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.utils.translation import gettext_lazy as _

from coldfront.views.object_actions import ObjectAction


class GenerateObject(ObjectAction):
    """
    (Re)generate the line items for a draft invoice.
    """

    name = "generate"
    label = _("Generate")
    multi = False
    transition = "generate"
    url_kwargs = ["pk"]
    permissions_required = {"generate"}
    template_name = "button.generate"


class InvoiceObject(ObjectAction):
    """
    Finalize a draft invoice (draft -> invoiced).
    """

    name = "invoice"
    label = _("Invoice")
    multi = False
    transition = "finalize"
    url_kwargs = ["pk"]
    permissions_required = {"finalize"}
    template_name = "button.invoice"


class PayObject(ObjectAction):
    """
    Record payment for an invoiced invoice (invoiced -> paid).
    """

    name = "pay"
    label = _("Pay")
    multi = False
    transition = "pay"
    url_kwargs = ["pk"]
    permissions_required = {"pay"}
    template_name = "button.pay"


class VoidObject(ObjectAction):
    """
    Void a draft or invoiced invoice (no refund).
    """

    name = "void"
    label = _("Void")
    multi = False
    transition = "void"
    url_kwargs = ["pk"]
    permissions_required = {"void"}
    template_name = "button.void"


class ExportPdfObject(ObjectAction):
    """
    Download a PDF rendering of the invoice.
    """

    name = "pdf"
    label = _("Export PDF")
    multi = False
    url_kwargs = ["pk"]
    permissions_required = {"view"}
    template_name = "button.pdf"
