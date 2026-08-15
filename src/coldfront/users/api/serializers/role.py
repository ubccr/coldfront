# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from coldfront.api.serializers import ValidatedModelSerializer
from coldfront.api.serializers.fields import SerializedPKRelatedField
from coldfront.users.models import Group, ObjectPermission, Role, User

from .nested import NestedGroupSerializer, NestedUserSerializer
from .permissions import ObjectPermissionSerializer


class RoleSerializer(ValidatedModelSerializer):
    object_permissions = SerializedPKRelatedField(
        queryset=ObjectPermission.objects.all(),
        serializer=ObjectPermissionSerializer,
        nested=True,
        required=False,
        many=True,
    )
    users = SerializedPKRelatedField(
        queryset=User.objects.all(),
        serializer=NestedUserSerializer,
        nested=True,
        required=False,
        many=True,
    )
    groups = SerializedPKRelatedField(
        queryset=Group.objects.all(),
        serializer=NestedGroupSerializer,
        nested=True,
        required=False,
        many=True,
    )

    class Meta:
        model = Role
        fields = (
            "id",
            "url",
            "display_url",
            "display",
            "name",
            "description",
            "weight",
            "object_permissions",
            "users",
            "groups",
        )
        brief_fields = (
            "id",
            "url",
            "display",
            "name",
            "description",
            "weight",
        )
