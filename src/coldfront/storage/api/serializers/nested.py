# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from coldfront.api.serializers import WritableNestedSerializer
from coldfront.storage import models

__all__ = (
    "NestedStorageClusterSerializer",
    "NestedStorageResourceSerializer",
    "NestedStorageQuotaSerializer",
    "NestedStorageSnapshotPolicySerializer",
)


class NestedStorageClusterSerializer(WritableNestedSerializer):
    class Meta:
        model = models.StorageCluster
        fields = ["id", "url", "display_url", "display", "name"]
        brief_fields = ("id", "url", "display", "name")


class NestedStorageResourceSerializer(WritableNestedSerializer):
    class Meta:
        model = models.StorageResource
        fields = ["id", "url", "display_url", "display", "name"]
        brief_fields = ("id", "url", "display", "name")


class NestedStorageQuotaSerializer(WritableNestedSerializer):
    class Meta:
        model = models.StorageQuota
        fields = ["id", "url", "display_url", "display", "path"]
        brief_fields = ("id", "url", "display", "path")


class NestedStorageSnapshotPolicySerializer(WritableNestedSerializer):
    class Meta:
        model = models.StorageSnapshotPolicy
        fields = ["id", "url", "display_url", "display", "name"]
        brief_fields = ("id", "url", "display", "name")
