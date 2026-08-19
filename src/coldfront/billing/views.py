# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _

from coldfront.billing import filtersets, forms, tables
from coldfront.billing import object_actions as actions
from coldfront.billing.flows import InvoiceStatusFlow, get_permitted_transition_actions
from coldfront.billing.models import (
    Discount,
    FreeAllowance,
    Invoice,
    InvoiceLineItem,
    Rate,
)
from coldfront.billing.pdf import render_invoice_pdf
from coldfront.registry import get_billing_sources, register_model_view
from coldfront.views import generic
from coldfront.views.mixins import GetRelatedModelsMixin

__all__ = (
    "DiscountBulkDeleteView",
    "DiscountBulkEditView",
    "DiscountBulkImportView",
    "DiscountDeleteView",
    "DiscountEditView",
    "DiscountListView",
    "DiscountView",
    "FreeAllowanceBulkDeleteView",
    "FreeAllowanceBulkEditView",
    "FreeAllowanceBulkImportView",
    "FreeAllowanceDeleteView",
    "FreeAllowanceEditView",
    "FreeAllowanceListView",
    "FreeAllowanceView",
    "InvoiceBulkDeleteView",
    "InvoiceBulkEditView",
    "InvoiceBulkImportView",
    "InvoiceDeleteView",
    "InvoiceEditView",
    "InvoiceBulkDeleteView",
    "InvoiceBulkEditView",
    "InvoiceBulkImportView",
    "InvoiceDeleteView",
    "InvoiceEditView",
    "InvoiceFinalizeView",
    "InvoiceGenerateView",
    "InvoicePayView",
    "InvoiceVoidView",
    "InvoiceLineItemListView",
    "InvoiceLineItemView",
    "InvoiceListView",
    "InvoiceView",
    "RateBulkDeleteView",
    "RateBulkEditView",
    "RateBulkImportView",
    "RateDeleteView",
    "RateEditView",
    "RateListView",
    "RateView",
)


#
# Invoices
#


@register_model_view(Invoice, "list", path="", detail=False)
class InvoiceListView(generic.ObjectListView):
    queryset = Invoice.objects.all()
    filterset = filtersets.InvoiceFilterSet
    filterset_form = forms.InvoiceFilterSetForm
    table = tables.InvoiceTable


@register_model_view(Invoice)
class InvoiceView(GetRelatedModelsMixin, generic.ObjectView):
    queryset = Invoice.objects.all()
    flow = InvoiceStatusFlow

    def get_extra_context(self, request, instance):
        transitions = get_permitted_transition_actions(instance, request.user)
        # The PDF export is always available to a viewer, regardless of status.
        transitions.append(actions.ExportPdfObject)
        return {
            "transitions": transitions,
            "related_models": self.get_related_models(request, instance),
        }


@register_model_view(Invoice, "pdf")
class InvoicePdfView(generic.ObjectView):
    queryset = Invoice.objects.all()

    def get(self, request, **kwargs):
        instance = self.get_object(**kwargs)
        response = HttpResponse(render_invoice_pdf(instance), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="invoice-{instance.slug}.pdf"'
        return response


class BaseInvoiceFlowView(generic.ObjectFlowView):
    queryset = Invoice.objects.all()
    form = forms.InvoiceTransitionForm
    flow = InvoiceStatusFlow


@register_model_view(Invoice, "generate")
class InvoiceGenerateView(BaseInvoiceFlowView):
    action = actions.GenerateObject


@register_model_view(Invoice, "invoice")
class InvoiceFinalizeView(BaseInvoiceFlowView):
    form = forms.InvoiceFinalizeForm
    action = actions.InvoiceObject


@register_model_view(Invoice, "pay")
class InvoicePayView(BaseInvoiceFlowView):
    form = forms.PaymentForm
    action = actions.PayObject


@register_model_view(Invoice, "void")
class InvoiceVoidView(BaseInvoiceFlowView):
    action = actions.VoidObject


@register_model_view(Invoice, "add", detail=False)
@register_model_view(Invoice, "edit")
class InvoiceEditView(generic.ObjectEditView):
    queryset = Invoice.objects.all()
    form = forms.InvoiceForm


@register_model_view(Invoice, "delete")
class InvoiceDeleteView(generic.ObjectDeleteView):
    queryset = Invoice.objects.all()


@register_model_view(Invoice, "bulk_import", path="import", detail=False)
class InvoiceBulkImportView(generic.BulkImportView):
    queryset = Invoice.objects.all()
    model_form = forms.InvoiceImportForm


@register_model_view(Invoice, "bulk_edit", path="edit", detail=False)
class InvoiceBulkEditView(generic.BulkEditView):
    queryset = Invoice.objects.all()
    filterset = filtersets.InvoiceFilterSet
    table = tables.InvoiceTable
    form = forms.InvoiceBulkEditForm


@register_model_view(Invoice, "bulk_delete", path="delete", detail=False)
class InvoiceBulkDeleteView(generic.BulkDeleteView):
    queryset = Invoice.objects.all()
    filterset = filtersets.InvoiceFilterSet
    table = tables.InvoiceTable


#
# Invoice Line Items
#


@register_model_view(InvoiceLineItem, "list", path="", detail=False)
class InvoiceLineItemListView(generic.ObjectListView):
    queryset = InvoiceLineItem.objects.all()
    filterset = filtersets.InvoiceLineItemFilterSet
    filterset_form = forms.InvoiceLineItemFilterSetForm
    table = tables.InvoiceLineItemTable


@register_model_view(InvoiceLineItem)
class InvoiceLineItemView(generic.ObjectView):
    queryset = InvoiceLineItem.objects.all()


@register_model_view(InvoiceLineItem, "add", detail=False)
@register_model_view(InvoiceLineItem, "edit")
class InvoiceLineItemEditView(generic.ObjectEditView):
    queryset = InvoiceLineItem.objects.all()
    form = forms.InvoiceLineItemForm


@register_model_view(InvoiceLineItem, "delete")
class InvoiceLineItemDeleteView(generic.ObjectDeleteView):
    queryset = InvoiceLineItem.objects.all()


@register_model_view(InvoiceLineItem, "bulk_edit", path="edit", detail=False)
class InvoiceLineItemBulkEditView(generic.BulkEditView):
    queryset = InvoiceLineItem.objects.all()
    filterset = filtersets.InvoiceLineItemFilterSet
    table = tables.InvoiceLineItemTable
    form = forms.InvoiceLineItemBulkEditForm


@register_model_view(InvoiceLineItem, "bulk_delete", path="delete", detail=False)
class InvoiceLineItemBulkDeleteView(generic.BulkDeleteView):
    queryset = InvoiceLineItem.objects.all()
    filterset = filtersets.InvoiceLineItemFilterSet
    table = tables.InvoiceLineItemTable


#
# Rates
#


@register_model_view(Rate, "list", path="", detail=False)
class RateListView(generic.ObjectListView):
    queryset = Rate.objects.all()
    filterset = filtersets.RateFilterSet
    filterset_form = forms.RateFilterSetForm
    table = tables.RateTable


@register_model_view(Rate)
class RateView(generic.ObjectView):
    queryset = Rate.objects.all()

    def get_extra_context(self, request, instance):
        hint = None
        if instance.scope_object is not None:
            sources = get_billing_sources(scope=instance.scope_object.__class__)
            if sources:
                labels = [f"{s['model']._meta.app_label}.{s['model']._meta.model_name}" for s in sources]
                hint = _("This rate bills: %(sources)s.") % {"sources": ", ".join(labels)}
        return {"billing_sources_hint": hint}


@register_model_view(Rate, "add", detail=False)
@register_model_view(Rate, "edit")
class RateEditView(GetRelatedModelsMixin, generic.ObjectEditView):
    queryset = Rate.objects.all()
    form = forms.RateForm
    template_name = "billing/rate_form.html"

    def get_extra_context(self, request, obj):
        hint, warning = None, None
        # With no registered billing sources, adding a Rate is meaningless; warn
        # like the generic missing-prereqs alert.
        if not get_billing_sources():
            warning = _("Before you can add a Rate, you must first register a billing source.")
        elif obj.pk and obj.scope_object is not None:
            sources = get_billing_sources(scope=obj.scope_object.__class__)
            if not sources:
                warning = _(
                    "No registered billable sources for this resource — nothing will be billed until one is configured."
                )
        return {
            "billing_sources_hint": hint,
            "billing_sources_warning": warning,
            "related_models": self.get_related_models(request, obj),
        }


@register_model_view(Rate, "delete")
class RateDeleteView(generic.ObjectDeleteView):
    queryset = Rate.objects.all()


@register_model_view(Rate, "bulk_import", path="import", detail=False)
class RateBulkImportView(generic.BulkImportView):
    queryset = Rate.objects.all()
    model_form = forms.RateImportForm


@register_model_view(Rate, "bulk_edit", path="edit", detail=False)
class RateBulkEditView(generic.BulkEditView):
    queryset = Rate.objects.all()
    filterset = filtersets.RateFilterSet
    table = tables.RateTable
    form = forms.RateBulkEditForm


@register_model_view(Rate, "bulk_delete", path="delete", detail=False)
class RateBulkDeleteView(generic.BulkDeleteView):
    queryset = Rate.objects.all()
    filterset = filtersets.RateFilterSet
    table = tables.RateTable


#
# Free Allowances
#


@register_model_view(FreeAllowance, "list", path="", detail=False)
class FreeAllowanceListView(generic.ObjectListView):
    queryset = FreeAllowance.objects.all()
    filterset = filtersets.FreeAllowanceFilterSet
    filterset_form = forms.FreeAllowanceFilterSetForm
    table = tables.FreeAllowanceTable


@register_model_view(FreeAllowance)
class FreeAllowanceView(generic.ObjectView):
    queryset = FreeAllowance.objects.all()


@register_model_view(FreeAllowance, "add", detail=False)
@register_model_view(FreeAllowance, "edit")
class FreeAllowanceEditView(generic.ObjectEditView):
    queryset = FreeAllowance.objects.all()
    form = forms.FreeAllowanceForm


@register_model_view(FreeAllowance, "delete")
class FreeAllowanceDeleteView(generic.ObjectDeleteView):
    queryset = FreeAllowance.objects.all()


@register_model_view(FreeAllowance, "bulk_import", path="import", detail=False)
class FreeAllowanceBulkImportView(generic.BulkImportView):
    queryset = FreeAllowance.objects.all()
    model_form = forms.FreeAllowanceImportForm


@register_model_view(FreeAllowance, "bulk_edit", path="edit", detail=False)
class FreeAllowanceBulkEditView(generic.BulkEditView):
    queryset = FreeAllowance.objects.all()
    filterset = filtersets.FreeAllowanceFilterSet
    table = tables.FreeAllowanceTable
    form = forms.FreeAllowanceBulkEditForm


@register_model_view(FreeAllowance, "bulk_delete", path="delete", detail=False)
class FreeAllowanceBulkDeleteView(generic.BulkDeleteView):
    queryset = FreeAllowance.objects.all()
    filterset = filtersets.FreeAllowanceFilterSet
    table = tables.FreeAllowanceTable


#
# Discounts
#


@register_model_view(Discount, "list", path="", detail=False)
class DiscountListView(generic.ObjectListView):
    queryset = Discount.objects.all()
    filterset = filtersets.DiscountFilterSet
    filterset_form = forms.DiscountFilterSetForm
    table = tables.DiscountTable


@register_model_view(Discount)
class DiscountView(generic.ObjectView):
    queryset = Discount.objects.all()


@register_model_view(Discount, "add", detail=False)
@register_model_view(Discount, "edit")
class DiscountEditView(generic.ObjectEditView):
    queryset = Discount.objects.all()
    form = forms.DiscountForm


@register_model_view(Discount, "delete")
class DiscountDeleteView(generic.ObjectDeleteView):
    queryset = Discount.objects.all()


@register_model_view(Discount, "bulk_import", path="import", detail=False)
class DiscountBulkImportView(generic.BulkImportView):
    queryset = Discount.objects.all()
    model_form = forms.DiscountImportForm


@register_model_view(Discount, "bulk_edit", path="edit", detail=False)
class DiscountBulkEditView(generic.BulkEditView):
    queryset = Discount.objects.all()
    filterset = filtersets.DiscountFilterSet
    table = tables.DiscountTable
    form = forms.DiscountBulkEditForm


@register_model_view(Discount, "bulk_delete", path="delete", detail=False)
class DiscountBulkDeleteView(generic.BulkDeleteView):
    queryset = Discount.objects.all()
    filterset = filtersets.DiscountFilterSet
    table = tables.DiscountTable
