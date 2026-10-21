# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from coldfront.core.models import ObjectType, Tag, TaggedItem
from coldfront.lib.api.exceptions import SerializerNotFound
from coldfront.lib.api.serializers import BaseModelSerializer, ChangeLogMessageSerializer, ValidatedModelSerializer
from coldfront.lib.api.serializers.fields import ContentTypeField, RelatedObjectCountField
from coldfront.lib.api.utils import get_serializer_for_model

__all__ = (
    "TagSerializer",
    "TaggedItemSerializer",
)


class TagSerializer(ChangeLogMessageSerializer, ValidatedModelSerializer):
    object_types = ContentTypeField(queryset=ObjectType.objects.with_feature("tags"), many=True, required=False)

    # Related object counts
    tagged_items = RelatedObjectCountField("core_taggeditem_items")

    class Meta:
        model = Tag
        fields = [
            "id",
            "url",
            "display_url",
            "display",
            "name",
            "slug",
            "color",
            "description",
            "weight",
            "object_types",
            "tagged_items",
            "created",
            "last_updated",
        ]
        brief_fields = ("id", "url", "display", "name", "slug", "color", "description")


class TaggedItemSerializer(BaseModelSerializer):
    object_type = ContentTypeField(source="content_type", read_only=True)
    object = serializers.SerializerMethodField(read_only=True)
    tag = TagSerializer(nested=True, read_only=True)

    class Meta:
        model = TaggedItem
        fields = [
            "id",
            "url",
            "display",
            "object_type",
            "object_id",
            "object",
            "tag",
        ]
        brief_fields = ("id", "url", "display", "object_type", "object_id", "object", "tag")

    @extend_schema_field(serializers.JSONField())
    def get_object(self, obj):
        """
        Serialize a nested representation of the tagged object.
        """
        try:
            serializer = get_serializer_for_model(obj.content_object)
        except SerializerNotFound:
            return obj.object_repr
        data = serializer(obj.content_object, nested=True, context={"request": self.context["request"]}).data

        return data
