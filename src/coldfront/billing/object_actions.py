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
    icon = "tablericon.wand"
    variant = "primary"
    modal = True
    multi = False
    transition = "generate"
    url_kwargs = ["pk"]
    permissions_required = {"generate"}


class InvoiceObject(ObjectAction):
    """
    Finalize a draft invoice (draft -> invoiced).
    """

    name = "invoice"
    label = _("Invoice")
    icon = "heroicon.document-text"
    variant = "success"
    modal = True
    multi = False
    transition = "finalize"
    url_kwargs = ["pk"]
    permissions_required = {"finalize"}


class PayObject(ObjectAction):
    """
    Record payment for an invoiced invoice (invoiced -> paid).
    """

    name = "pay"
    label = _("Pay")
    icon = "tablericon.currency-dollar"
    variant = "success"
    modal = True
    multi = False
    transition = "pay"
    url_kwargs = ["pk"]
    permissions_required = {"pay"}


class VoidObject(ObjectAction):
    """
    Void a draft or invoiced invoice (no refund).
    """

    name = "void"
    label = _("Void")
    icon = "tablericon.forbid"
    variant = "error"
    modal = True
    multi = False
    transition = "void"
    url_kwargs = ["pk"]
    permissions_required = {"void"}


class ExportPdfObject(ObjectAction):
    """
    Download a PDF rendering of the invoice.
    """

    name = "pdf"
    label = _("Export PDF")
    icon = "tablericon.file-type-pdf"
    variant = "secondary"
    as_ = "a"
    multi = False
    url_kwargs = ["pk"]
    permissions_required = {"view"}
