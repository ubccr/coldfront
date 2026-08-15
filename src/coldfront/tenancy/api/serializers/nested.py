# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from coldfront.api.serializers import WritableNestedSerializer
from coldfront.tenancy import models

__all__ = ("NestedTenantGroupSerializer",)


@extend_schema_serializer(
    exclude_fields=("tenant_count",),
)
class NestedTenantGroupSerializer(WritableNestedSerializer):
    tenant_count = serializers.IntegerField(read_only=True)
    _depth = serializers.IntegerField(source="level", read_only=True)

    class Meta:
        model = models.TenantGroup
        fields = ["id", "url", "display_url", "display", "name", "slug", "tenant_count", "_depth"]
