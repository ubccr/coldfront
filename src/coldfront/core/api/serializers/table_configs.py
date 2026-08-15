# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from coldfront.api.serializers import ChangeLogMessageSerializer, ValidatedModelSerializer
from coldfront.api.serializers.fields import ContentTypeField
from coldfront.core.models import ObjectType, TableConfig

__all__ = ("TableConfigSerializer",)


class TableConfigSerializer(ChangeLogMessageSerializer, ValidatedModelSerializer):
    object_type = ContentTypeField(
        queryset=ObjectType.objects.all(),
    )

    class Meta:
        model = TableConfig
        fields = [
            "id",
            "url",
            "display_url",
            "display",
            "object_type",
            "table",
            "name",
            "description",
            "user",
            "weight",
            "enabled",
            "shared",
            "columns",
            "ordering",
            "created",
            "last_updated",
        ]
        brief_fields = ("id", "url", "display", "name", "description", "object_type", "table")
