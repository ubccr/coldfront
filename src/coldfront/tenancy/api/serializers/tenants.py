# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from rest_framework import serializers

from coldfront.api.serializers import NestedGroupModelSerializer, PrimaryModelSerializer
from coldfront.api.serializers.fields import RelatedObjectCountField
from coldfront.tenancy.models import Tenant, TenantGroup

from .nested import NestedTenantGroupSerializer

__all__ = (
    "TenantGroupSerializer",
    "TenantSerializer",
)


class TenantGroupSerializer(NestedGroupModelSerializer):
    parent = NestedTenantGroupSerializer(required=False, allow_null=True)
    tenant_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = TenantGroup
        fields = [
            "id",
            "url",
            "display_url",
            "display",
            "name",
            "slug",
            "parent",
            "description",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
            "tenant_count",
            "_depth",
        ]
        brief_fields = ("id", "url", "display", "name", "slug", "description", "tenant_count", "_depth")


class TenantSerializer(PrimaryModelSerializer):
    group = TenantGroupSerializer(nested=True, required=False, allow_null=True, default=None)

    # Related object counts
    project_count = RelatedObjectCountField("projects")

    class Meta:
        model = Tenant
        fields = [
            "id",
            "url",
            "display_url",
            "display",
            "name",
            "slug",
            "group",
            "description",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
            "project_count",
        ]
        brief_fields = ("id", "url", "display", "name", "slug", "description")
