# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from rest_framework.routers import APIRootView

from coldfront.api.viewsets import ColdFrontModelViewSet
from coldfront.billing import filtersets
from coldfront.billing.models import (
    Discount,
    FreeAllowance,
    Invoice,
    InvoiceLineItem,
    Rate,
)

from . import serializers

__all__ = (
    "BillingRootView",
    "DiscountViewSet",
    "FreeAllowanceViewSet",
    "InvoiceLineItemViewSet",
    "InvoiceViewSet",
    "RateViewSet",
)


class BillingRootView(APIRootView):
    """
    Billing API root view
    """

    def get_view_name(self):
        return "Billing"


class InvoiceViewSet(ColdFrontModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = serializers.InvoiceSerializer
    filterset_class = filtersets.InvoiceFilterSet


class InvoiceLineItemViewSet(ColdFrontModelViewSet):
    queryset = InvoiceLineItem.objects.all()
    serializer_class = serializers.InvoiceLineItemSerializer
    filterset_class = filtersets.InvoiceLineItemFilterSet


class RateViewSet(ColdFrontModelViewSet):
    queryset = Rate.objects.all()
    serializer_class = serializers.RateSerializer
    filterset_class = filtersets.RateFilterSet


class FreeAllowanceViewSet(ColdFrontModelViewSet):
    queryset = FreeAllowance.objects.all()
    serializer_class = serializers.FreeAllowanceSerializer
    filterset_class = filtersets.FreeAllowanceFilterSet


class DiscountViewSet(ColdFrontModelViewSet):
    queryset = Discount.objects.all()
    serializer_class = serializers.DiscountSerializer
    filterset_class = filtersets.DiscountFilterSet
