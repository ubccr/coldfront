# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from coldfront.api.serializers import WritableNestedSerializer
from coldfront.billing import models

__all__ = (
    "NestedDiscountSerializer",
    "NestedFreeAllowanceSerializer",
    "NestedInvoiceLineItemSerializer",
    "NestedInvoiceSerializer",
    "NestedRateSerializer",
)


class NestedInvoiceSerializer(WritableNestedSerializer):
    class Meta:
        model = models.Invoice
        fields = ["id", "url", "display_url", "display", "slug"]
        brief_fields = ("id", "url", "display", "slug")


class NestedInvoiceLineItemSerializer(WritableNestedSerializer):
    class Meta:
        model = models.InvoiceLineItem
        fields = ["id", "url", "display_url", "display", "line_type"]
        brief_fields = ("id", "url", "display", "line_type")


class NestedRateSerializer(WritableNestedSerializer):
    class Meta:
        model = models.Rate
        fields = ["id", "url", "display_url", "display"]
        brief_fields = ("id", "url", "display")


class NestedFreeAllowanceSerializer(WritableNestedSerializer):
    class Meta:
        model = models.FreeAllowance
        fields = ["id", "url", "display_url", "display"]
        brief_fields = ("id", "url", "display")


class NestedDiscountSerializer(WritableNestedSerializer):
    class Meta:
        model = models.Discount
        fields = ["id", "url", "display_url", "display"]
        brief_fields = ("id", "url", "display")
