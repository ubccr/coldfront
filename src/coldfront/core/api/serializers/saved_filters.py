# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from coldfront.core.models import ObjectType, SavedFilter
from coldfront.lib.api.serializers import ChangeLogMessageSerializer, ValidatedModelSerializer
from coldfront.lib.api.serializers.fields import ContentTypeField

__all__ = ("SavedFilterSerializer",)


class SavedFilterSerializer(ChangeLogMessageSerializer, ValidatedModelSerializer):
    object_types = ContentTypeField(
        queryset=ObjectType.objects.all(),
        many=True,
    )

    class Meta:
        model = SavedFilter
        fields = [
            "id",
            "url",
            "display_url",
            "display",
            "object_types",
            "name",
            "slug",
            "description",
            "user",
            "weight",
            "enabled",
            "shared",
            "parameters",
            "created",
            "last_updated",
        ]
        brief_fields = ("id", "url", "display", "name", "slug", "description")
