# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from coldfront.api.serializers import ChangeLogMessageSerializer, PrimaryModelSerializer, ValidatedModelSerializer
from coldfront.api.serializers.fields import ChoiceField, ContentTypeField, MoneyField
from coldfront.billing.choices import (
    InvoiceLineTypeChoices,
    InvoiceStatusChoices,
    PaymentMethodChoices,
    UnitFormatChoiceSet,
)
from coldfront.billing.models import Invoice, InvoiceLineItem
from coldfront.users.api.serializers import UserSerializer

from .nested import NestedInvoiceSerializer

__all__ = ("InvoiceLineItemSerializer", "InvoiceSerializer")


class InvoiceSerializer(PrimaryModelSerializer):
    owner = UserSerializer(nested=True)
    status = ChoiceField(choices=InvoiceStatusChoices, required=False)
    payment_method = ChoiceField(choices=PaymentMethodChoices, required=False)
    source_types = serializers.SerializerMethodField(read_only=True)

    payment_amount = MoneyField(required=False)
    payment_amount_currency = serializers.CharField(read_only=True)
    subtotal = MoneyField(required=False)
    subtotal_currency = serializers.CharField(read_only=True)
    allowance_total = MoneyField(required=False)
    allowance_total_currency = serializers.CharField(read_only=True)
    discount_total = MoneyField(required=False)
    discount_total_currency = serializers.CharField(read_only=True)
    grand_total = MoneyField(required=False)
    grand_total_currency = serializers.CharField(read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id",
            "url",
            "display_url",
            "display",
            "slug",
            "owner",
            "source_types",
            "start_date",
            "end_date",
            "due_date",
            "status",
            "payment_date",
            "payment_amount",
            "payment_amount_currency",
            "payment_method",
            "subtotal",
            "subtotal_currency",
            "allowance_total",
            "allowance_total_currency",
            "discount_total",
            "discount_total_currency",
            "grand_total",
            "grand_total_currency",
            "description",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
        ]
        brief_fields = ("id", "url", "display", "slug", "owner", "status", "due_date")

    def get_source_types(self, obj):
        return [f"{ct.app_label}.{ct.model}" for ct in obj.source_types.all().order_by("app_label", "model")]


class InvoiceLineItemSerializer(ChangeLogMessageSerializer, ValidatedModelSerializer):
    invoice = NestedInvoiceSerializer(nested=True)
    line_type = ChoiceField(choices=InvoiceLineTypeChoices, required=False)
    source_object = serializers.SerializerMethodField(read_only=True)
    source_object_type = ContentTypeField(queryset=ContentType.objects.all(), required=False)
    source_object_id = serializers.IntegerField(required=False)
    unit = serializers.CharField(required=False, allow_blank=True)
    unit_format = ChoiceField(choices=UnitFormatChoiceSet, required=False)

    unit_price = MoneyField(required=False)
    unit_price_currency = serializers.CharField(read_only=True)
    amount = MoneyField(required=False)
    amount_currency = serializers.CharField(read_only=True)

    class Meta:
        model = InvoiceLineItem
        fields = [
            "id",
            "url",
            "display_url",
            "display",
            "invoice",
            "line_type",
            "source_object",
            "source_object_type",
            "source_object_id",
            "description",
            "is_valid",
            "quantity",
            "unit",
            "unit_format",
            "unit_price",
            "unit_price_currency",
            "amount",
            "amount_currency",
            "created",
            "last_updated",
        ]
        brief_fields = ("id", "url", "display", "invoice", "line_type", "quantity", "unit", "unit_format")

    def get_source_object(self, obj):
        source = obj.source_object
        if source is None:
            return None
        ct = obj.source_object_type
        return {
            "id": obj.source_object_id,
            "type": f"{ct.app_label}.{ct.model}" if ct else None,
            "display": str(source),
        }
