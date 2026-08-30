# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from coldfront.api.serializers import PrimaryModelSerializer
from coldfront.api.serializers.fields import ChoiceField, ContentTypeField, MoneyField
from coldfront.billing.choices import ChargeBasisChoices, UnitFormatChoiceSet
from coldfront.billing.models import Rate

__all__ = ("RateSerializer",)


class RateSerializer(PrimaryModelSerializer):
    scope_object = serializers.SerializerMethodField(read_only=True)
    scope_object_type = ContentTypeField(queryset=ContentType.objects.all(), required=False)
    scope_object_id = serializers.IntegerField(required=False)
    unit = serializers.IntegerField(required=False)
    unit_format = ChoiceField(choices=UnitFormatChoiceSet, required=False)
    amount = MoneyField(required=False)
    amount_currency = serializers.CharField(read_only=True)
    charge_basis = ChoiceField(choices=ChargeBasisChoices, required=False)

    class Meta:
        model = Rate
        fields = [
            "id",
            "url",
            "display_url",
            "display",
            "name",
            "scope_object",
            "scope_object_type",
            "scope_object_id",
            "unit",
            "unit_format",
            "amount",
            "amount_currency",
            "charge_basis",
            "effective_start",
            "effective_end",
            "description",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
        ]
        brief_fields = ("id", "url", "display", "name", "unit", "unit_format", "amount", "charge_basis")

    def get_scope_object(self, obj):
        scope = obj.scope_object
        if scope is None:
            return None
        ct = obj.scope_object_type
        return {
            "id": obj.scope_object_id,
            "type": f"{ct.app_label}.{ct.model}" if ct else None,
            "display": str(scope),
        }
