# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from coldfront.api.serializers import PrimaryModelSerializer
from coldfront.api.serializers.fields import ChoiceField, ContentTypeField
from coldfront.billing.choices import DiscountTypeChoices, UnitFormatChoiceSet
from coldfront.billing.models import Discount, FreeAllowance
from coldfront.users.api.serializers import UserSerializer

__all__ = ("DiscountSerializer", "FreeAllowanceSerializer")


class FreeAllowanceSerializer(PrimaryModelSerializer):
    owner = UserSerializer(nested=True)
    scope_object = serializers.SerializerMethodField(read_only=True)
    scope_object_type = ContentTypeField(queryset=ContentType.objects.all(), required=False)
    scope_object_id = serializers.IntegerField(required=False)
    unit_format = ChoiceField(choices=UnitFormatChoiceSet)

    class Meta:
        model = FreeAllowance
        fields = [
            "id",
            "url",
            "display_url",
            "display",
            "name",
            "owner",
            "scope_object",
            "scope_object_type",
            "scope_object_id",
            "unit_format",
            "quantity_total",
            "used",
            "start_date",
            "end_date",
            "description",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
        ]
        brief_fields = ("id", "url", "display", "name", "owner", "unit_format", "quantity_total", "used")

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


class DiscountSerializer(PrimaryModelSerializer):
    owner = UserSerializer(nested=True, required=False, allow_null=True, default=None)
    scope_object = serializers.SerializerMethodField(read_only=True)
    scope_object_type = ContentTypeField(queryset=ContentType.objects.all(), required=False)
    scope_object_id = serializers.IntegerField(required=False)
    type = ChoiceField(choices=DiscountTypeChoices, required=False)

    class Meta:
        model = Discount
        fields = [
            "id",
            "url",
            "display_url",
            "display",
            "name",
            "owner",
            "scope_object",
            "scope_object_type",
            "scope_object_id",
            "type",
            "value",
            "description",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
        ]
        brief_fields = ("id", "url", "display", "name", "owner", "type", "value")

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
