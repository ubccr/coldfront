# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from coldfront.api.serializers import (
    CustomAttributeModelSerializer,
    PrimaryModelSerializer,
)
from coldfront.api.serializers.fields import ContentTypeField
from coldfront.ras.models import Allocation
from coldfront.users.api.serializers import UserSerializer

from .projects import ProjectSerializer


class AllocationSerializer(CustomAttributeModelSerializer, PrimaryModelSerializer):
    owner = UserSerializer(nested=True)
    project = ProjectSerializer(nested=True)
    resource_object = serializers.SerializerMethodField(read_only=True)
    resource_object_type = ContentTypeField(queryset=ContentType.objects.all(), required=False)
    resource_object_id = serializers.IntegerField(required=False)

    class Meta:
        model = Allocation
        fields = [
            "id",
            "url",
            "display_url",
            "display",
            "slug",
            "description",
            "justification",
            "status",
            "owner",
            "project",
            "resource_object",
            "resource_object_type",
            "resource_object_id",
            "start_date",
            "end_date",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
            "attributes",
        ]
        brief_fields = ("id", "url", "display", "id", "slug", "description", "status")

    def get_resource_object(self, obj):
        """Return a serialized representation of the generic resource object."""
        resource = obj.resource_object
        if resource is None:
            return None
        # Build a simple representation with id, type, and string display
        ct = obj.resource_object_type
        return {
            "id": obj.resource_object_id,
            "type": f"{ct.app_label}.{ct.model}" if ct else None,
            "display": str(resource),
        }
