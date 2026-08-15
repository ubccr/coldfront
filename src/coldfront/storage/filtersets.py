# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import django_filters
from django.db.models import Q
from django.utils.translation import gettext as _

from coldfront.ras.models import Allocation
from coldfront.storage.choices import StorageShareTypeChoices
from coldfront.storage.models import StorageCluster, StorageQuota, StorageResource, StorageSnapshotPolicy
from coldfront.tenancy.filtersets import TenancyFilterSet
from coldfront.views.filtersets import PrimaryModelFilterSet


class StorageResourceFilterSet(TenancyFilterSet, PrimaryModelFilterSet):
    clusters = django_filters.ModelMultipleChoiceFilter(
        queryset=StorageCluster.objects.all(),
        distinct=False,
        label=_("Clusters"),
    )
    locked = django_filters.BooleanFilter(
        label=_("Locked"),
    )

    class Meta:
        model = StorageResource
        fields = (
            "id",
            "name",
            "description",
            "clusters",
            "locked",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(name__icontains=value) | Q(description__icontains=value))


class StorageClusterFilterSet(PrimaryModelFilterSet):
    backend_path = django_filters.CharFilter(
        field_name="backend_path",
        lookup_expr="icontains",
        label=_("Backend Path"),
    )
    auto_sync_enabled = django_filters.BooleanFilter(
        label=_("Auto Sync Enabled"),
    )

    class Meta:
        model = StorageCluster
        fields = (
            "id",
            "name",
            "description",
            "backend_path",
            "auto_sync_enabled",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(name__icontains=value) | Q(description__icontains=value))


class StorageQuotaFilterSet(PrimaryModelFilterSet):
    storage_id = django_filters.ModelMultipleChoiceFilter(
        queryset=StorageResource.objects.all(),
        distinct=False,
        label=_("Storage Resource (ID)"),
    )
    storage = django_filters.ModelMultipleChoiceFilter(
        field_name="storage__name",
        queryset=StorageResource.objects.all(),
        distinct=False,
        to_field_name="name",
        label=_("Storage Resource (name)"),
    )
    allocation_id = django_filters.ModelChoiceFilter(
        field_name="allocation",
        queryset=Allocation.objects.all(),
        label=_("Allocation"),
    )
    share_type = django_filters.ChoiceFilter(
        choices=StorageShareTypeChoices,
    )
    snapshot_policy_id = django_filters.ModelChoiceFilter(
        field_name="snapshot_policy",
        queryset=StorageSnapshotPolicy.objects.all(),
        label=_("Snapshot Policy"),
    )

    class Meta:
        model = StorageQuota
        fields = (
            "id",
            "storage",
            "path",
            "owning_user",
            "owning_group",
            "state",
            "allocation_id",
            "share_type",
            "snapshot_policy_id",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(path__icontains=value) | Q(owning_user__icontains=value) | Q(owning_group__icontains=value)
        )


class StorageSnapshotPolicyFilterSet(PrimaryModelFilterSet):
    cluster_id = django_filters.ModelMultipleChoiceFilter(
        queryset=StorageCluster.objects.all(),
        distinct=False,
        label=_("Cluster (ID)"),
    )
    cluster = django_filters.ModelMultipleChoiceFilter(
        field_name="cluster__name",
        queryset=StorageCluster.objects.all(),
        distinct=False,
        to_field_name="name",
        label=_("Cluster (name)"),
    )
    retention_days = django_filters.NumberFilter(
        label=_("Retention Days"),
    )

    class Meta:
        model = StorageSnapshotPolicy
        fields = (
            "id",
            "cluster",
            "name",
            "interval",
            "retention_days",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(name__icontains=value))
