# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from coldfront.api.serializers import ValidatedModelSerializer
from coldfront.api.serializers.fields import ContentTypeField, SerializedPKRelatedField
from coldfront.core.models import ObjectType
from coldfront.users.models import Group, ObjectPermission, User

from .nested import NestedGroupSerializer, NestedUserSerializer


class ObjectPermissionSerializer(ValidatedModelSerializer):
    object_types = ContentTypeField(queryset=ObjectType.objects.all(), many=True)
    groups = SerializedPKRelatedField(
        queryset=Group.objects.all(), serializer=NestedGroupSerializer, nested=True, required=False, many=True
    )
    users = SerializedPKRelatedField(
        queryset=User.objects.all(), serializer=NestedUserSerializer, nested=True, required=False, many=True
    )

    class Meta:
        model = ObjectPermission
        fields = (
            "id",
            "url",
            "display_url",
            "display",
            "name",
            "description",
            "enabled",
            "object_types",
            "actions",
            "constraints",
            "groups",
            "users",
        )
        brief_fields = (
            "id",
            "url",
            "display",
            "name",
            "description",
            "enabled",
            "object_types",
            "actions",
        )
