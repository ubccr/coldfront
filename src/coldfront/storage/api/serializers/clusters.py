# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from coldfront.api.serializers import AllocatableResourceModelSerializer, PrimaryModelSerializer
from coldfront.api.serializers.fields import RelatedObjectCountField
from coldfront.storage.models import (
    StorageCluster,
    StorageQuota,
    StorageResource,
    StorageSnapshotPolicy,
)
from coldfront.tenancy.api.serializers.tenants import TenantSerializer
from coldfront.users.api.serializers import GroupSerializer, UserSerializer

from .nested import (
    NestedStorageClusterSerializer,
    NestedStorageResourceSerializer,
    NestedStorageSnapshotPolicySerializer,
)


class StorageSnapshotPolicySerializer(PrimaryModelSerializer):
    class Meta:
        model = StorageSnapshotPolicy
        fields = [
            "id",
            "url",
            "display_url",
            "display",
            "cluster",
            "name",
            "description",
            "interval",
            "retention_days",
            "extra_config",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
        ]
        brief_fields = ("id", "url", "display", "name", "description", "interval", "retention_days")


class StorageClusterSerializer(AllocatableResourceModelSerializer, PrimaryModelSerializer):
    quota_count = RelatedObjectCountField("quotas")
    snapshot_policy_count = RelatedObjectCountField("snapshot_policies")

    class Meta:
        model = StorageCluster
        fields = [
            "id",
            "url",
            "display_url",
            "display",
            "name",
            "description",
            "backend_path",
            "auto_sync_enabled",
            "sync_interval",
            "capacity_bytes",
            "allocated_bytes",
            "used_bytes",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
            "quota_count",
            "snapshot_policy_count",
        ]
        brief_fields = ("id", "url", "display", "name", "description", "backend_path", "capacity_bytes")


class StorageResourceSerializer(AllocatableResourceModelSerializer, PrimaryModelSerializer):
    tenant = TenantSerializer(nested=True, required=False, allow_null=True, default=None)
    clusters = NestedStorageClusterSerializer(nested=True, many=True, required=False)
    quota_count = RelatedObjectCountField("quotas")

    class Meta:
        model = StorageResource
        fields = [
            "id",
            "url",
            "display_url",
            "display",
            "name",
            "tenant",
            "description",
            "locked",
            "schema",
            "clusters",
            "path_template",
            "capacity_bytes",
            "allocated_bytes",
            "used_bytes",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
            "quota_count",
        ]
        brief_fields = ("id", "url", "display", "name", "description", "locked", "capacity_bytes")

    def create(self, validated_data):
        clusters = validated_data.pop("clusters", None)
        instance = super().create(validated_data)
        if clusters is not None:
            instance.clusters.set(clusters)
        return instance

    def update(self, instance, validated_data):
        clusters = validated_data.pop("clusters", None)
        instance = super().update(instance, validated_data)
        if clusters is not None:
            instance.clusters.set(clusters)
        return instance


class StorageQuotaSerializer(PrimaryModelSerializer):
    storage = NestedStorageResourceSerializer(nested=True)
    clusters = NestedStorageClusterSerializer(nested=True, many=True, required=False)
    owning_user = UserSerializer(nested=True)
    owning_group = GroupSerializer(nested=True)
    snapshot_policy = NestedStorageSnapshotPolicySerializer(nested=True, required=False, allow_null=True, default=None)

    class Meta:
        model = StorageQuota
        fields = [
            "id",
            "url",
            "display_url",
            "display",
            "allocation",
            "storage",
            "clusters",
            "path",
            "owning_user",
            "owning_group",
            "path_mode",
            "hard_limit_bytes",
            "soft_limit_bytes",
            "hard_limit_files",
            "soft_limit_files",
            "grace_period",
            "share_type",
            "used",
            "used_files",
            "state",
            "snapshot_policy",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
        ]
        brief_fields = (
            "id",
            "url",
            "display",
            "allocation",
            "storage",
            "path",
            "hard_limit_bytes",
            "share_type",
        )
