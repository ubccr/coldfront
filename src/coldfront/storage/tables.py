# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import django_tables2 as tables
from django.utils.translation import gettext_lazy as _

from coldfront.storage.models import StorageCluster, StorageQuota, StorageResource, StorageSnapshotPolicy
from coldfront.tables import PrimaryModelTable, columns
from coldfront.tenancy.tables.columns import TenancyColumnsMixin


class StorageResourceTable(TenancyColumnsMixin, PrimaryModelTable):
    name = tables.Column(
        verbose_name=_("Name"),
        linkify=True,
    )
    tags = columns.TagColumn(
        url_name="storage:storageresource_list",
    )

    capacity_bytes = columns.BytesColumn()

    class Meta(PrimaryModelTable.Meta):
        model = StorageResource
        fields = (
            "pk",
            "id",
            "name",
            "description",
            "clusters",
            "path_template",
            "capacity_bytes",
            "allocated_bytes",
            "used_bytes",
            "tenant",
            "tags",
            "created",
            "last_updated",
        )
        default_columns = ("pk", "name", "description", "clusters", "capacity_bytes")


class StorageClusterTable(PrimaryModelTable):
    name = tables.Column(
        verbose_name=_("Name"),
        linkify=True,
    )
    tags = columns.TagColumn(
        url_name="storage:storagecluster_list",
    )
    capacity_bytes = columns.BytesColumn()

    class Meta(PrimaryModelTable.Meta):
        model = StorageCluster
        fields = (
            "pk",
            "id",
            "name",
            "description",
            "backend_path",
            "auto_sync_enabled",
            "sync_interval",
            "capacity_bytes",
            "allocated_bytes",
            "used_bytes",
            "tags",
            "created",
            "last_updated",
        )
        default_columns = ("pk", "name", "description", "backend_path", "capacity_bytes")


class StorageQuotaTable(PrimaryModelTable):
    path = tables.Column(
        verbose_name=_("Path"),
        linkify=True,
    )
    tags = columns.TagColumn(
        url_name="storage:storagequota_list",
    )
    hard_limit_bytes = columns.BytesColumn()
    soft_limit_bytes = columns.BytesColumn()

    class Meta(PrimaryModelTable.Meta):
        model = StorageQuota
        fields = (
            "pk",
            "id",
            "path",
            "storage",
            "clusters",
            "allocation",
            "owning_user",
            "owning_group",
            "path_mode",
            "hard_limit_bytes",
            "soft_limit_bytes",
            "hard_limit_files",
            "soft_limit_files",
            "share_type",
            "used",
            "used_files",
            "state",
            "snapshot_policy",
            "tags",
            "created",
            "last_updated",
        )
        default_columns = ("pk", "path", "storage", "allocation", "hard_limit_bytes", "used", "state")


class StorageSnapshotPolicyTable(PrimaryModelTable):
    name = tables.Column(
        verbose_name=_("Name"),
        linkify=True,
    )
    tags = columns.TagColumn(
        url_name="storage:storagesnapshotpolicy_list",
    )

    class Meta(PrimaryModelTable.Meta):
        model = StorageSnapshotPolicy
        fields = (
            "pk",
            "id",
            "name",
            "cluster",
            "interval",
            "retention_days",
            "tags",
            "created",
            "last_updated",
        )
        default_columns = ("pk", "name", "cluster", "interval", "retention_days")
