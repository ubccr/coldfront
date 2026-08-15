# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field

from coldfront.api.serializers import WritableNestedSerializer
from coldfront.users import models

__all__ = (
    "NestedGroupSerializer",
    "NestedRoleSerializer",
    "NestedUserSerializer",
)


class NestedGroupSerializer(WritableNestedSerializer):
    class Meta:
        model = models.Group
        fields = ["id", "url", "display_url", "display", "name"]
        brief_fields = ("id", "url", "display", "name")


class NestedRoleSerializer(WritableNestedSerializer):
    class Meta:
        model = models.Role
        fields = ["id", "url", "display_url", "display", "name", "weight"]
        brief_fields = ("id", "url", "display", "name", "weight")


class NestedUserSerializer(WritableNestedSerializer):
    class Meta:
        model = models.User
        fields = ["id", "url", "display_url", "display", "username"]
        brief_fields = ("id", "url", "display", "username")

    @extend_schema_field(OpenApiTypes.STR)
    def get_display(self, obj):
        if full_name := obj.get_full_name():
            return f"{obj.username} ({full_name})"
        return obj.username
