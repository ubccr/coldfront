# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0


from coldfront.api.serializers import (
    AllocatableResourceModelSerializer,
    NestedGroupModelSerializer,
    OrganizationalModelSerializer,
)
from coldfront.api.serializers.fields import RelatedObjectCountField
from coldfront.ras.models import Resource, ResourceType

from .nested import NestedResourceSerializer


class ResourceTypeSerializer(OrganizationalModelSerializer):
    resource_count = RelatedObjectCountField("resources")

    class Meta:
        model = ResourceType
        fields = [
            "id",
            "url",
            "display_url",
            "display",
            "name",
            "slug",
            "description",
            "color",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
            "resource_count",
        ]
        brief_fields = ("id", "url", "display", "name", "description", "slug")


class ResourceSerializer(AllocatableResourceModelSerializer, NestedGroupModelSerializer):
    parent = NestedResourceSerializer(required=False, allow_null=True, default=None)
    allocation_count = RelatedObjectCountField("allocations")
    resource_type = ResourceTypeSerializer(nested=True)

    class Meta:
        model = Resource
        fields = [
            "id",
            "url",
            "display_url",
            "display",
            "name",
            "slug",
            "parent",
            "_depth",
            "description",
            "status",
            "locked",
            "resource_type",
            "tags",
            "schema",
            "custom_fields",
            "created",
            "last_updated",
            "allocation_count",
        ]
        brief_fields = ("id", "url", "display", "name", "slug", "description", "status", "_depth")
