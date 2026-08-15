# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import django_filters
from django.db.models import Q
from django.utils.translation import gettext as _

from coldfront.ras.models import Allocation
from coldfront.slurm.models import (
    SlurmAccount,
    SlurmAssociation,
    SlurmCluster,
    SlurmPartition,
    SlurmQOS,
    SlurmUser,
)
from coldfront.tenancy.filtersets import TenancyFilterSet
from coldfront.users.models import User
from coldfront.views.filtersets import PrimaryModelFilterSet


class SlurmQOSFilterSet(PrimaryModelFilterSet):
    class Meta:
        model = SlurmQOS
        fields = (
            "id",
            "name",
            "description",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(name__icontains=value) | Q(description__icontains=value))


class SlurmClusterFilterSet(TenancyFilterSet, PrimaryModelFilterSet):
    locked = django_filters.BooleanFilter(
        label=_("Locked"),
    )
    default_qos_id = django_filters.ModelChoiceFilter(
        field_name="default_qos",
        queryset=SlurmQOS.objects.all(),
        label=_("Default QOS"),
    )
    classification = django_filters.CharFilter(
        field_name="classification",
        lookup_expr="icontains",
        label=_("Classification"),
    )

    class Meta:
        model = SlurmCluster
        fields = (
            "id",
            "name",
            "description",
            "locked",
            "default_qos_id",
            "classification",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(name__icontains=value) | Q(description__icontains=value))


class SlurmPartitionFilterSet(PrimaryModelFilterSet):
    cluster_id = django_filters.ModelMultipleChoiceFilter(
        queryset=SlurmCluster.objects.all(),
        distinct=False,
        label=_("Cluster (ID)"),
    )
    cluster = django_filters.ModelMultipleChoiceFilter(
        field_name="cluster__name",
        queryset=SlurmCluster.objects.all(),
        distinct=False,
        to_field_name="name",
        label=_("Cluster (name)"),
    )
    qos_id = django_filters.ModelChoiceFilter(
        field_name="qos",
        queryset=SlurmQOS.objects.all(),
        label=_("QOS"),
    )
    locked = django_filters.BooleanFilter(
        label=_("Locked"),
    )

    class Meta:
        model = SlurmPartition
        fields = (
            "id",
            "cluster",
            "name",
            "slug",
            "description",
            "nodes",
            "priority",
            "is_default",
            "state",
            "preempt_mode",
            "qos_id",
            "locked",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(name__icontains=value) | Q(description__icontains=value))


class SlurmAccountFilterSet(PrimaryModelFilterSet):
    cluster_id = django_filters.ModelMultipleChoiceFilter(
        queryset=SlurmCluster.objects.all(),
        distinct=False,
        label=_("Cluster (ID)"),
    )
    cluster = django_filters.ModelMultipleChoiceFilter(
        field_name="cluster__name",
        queryset=SlurmCluster.objects.all(),
        distinct=False,
        to_field_name="name",
        label=_("Cluster (name)"),
    )

    class Meta:
        model = SlurmAccount
        fields = (
            "id",
            "cluster",
            "name",
            "description",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(name__icontains=value) | Q(description__icontains=value))


class SlurmAssociationFilterSet(PrimaryModelFilterSet):
    slurm_account_id = django_filters.ModelChoiceFilter(
        queryset=SlurmAccount.objects.all(),
        label=_("Slurm Account"),
    )
    allocation_id = django_filters.ModelChoiceFilter(
        field_name="allocation",
        queryset=Allocation.objects.all(),
        label=_("Allocation"),
    )
    parent_id = django_filters.ModelChoiceFilter(
        field_name="parent",
        queryset=SlurmAccount.objects.all(),
        label=_("Parent Account"),
    )
    default_qos_id = django_filters.ModelChoiceFilter(
        field_name="default_qos",
        queryset=SlurmQOS.objects.all(),
        label=_("Default QOS"),
    )

    class Meta:
        model = SlurmAssociation
        fields = (
            "id",
            "slurm_account",
            "fairshare",
            "allocation_id",
            "parent_id",
            "default_qos_id",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(allocation__slug__icontains=value))


class SlurmUserFilterSet(PrimaryModelFilterSet):
    cluster_id = django_filters.ModelMultipleChoiceFilter(
        queryset=SlurmCluster.objects.all(),
        distinct=False,
        label=_("Cluster (ID)"),
    )
    cluster = django_filters.ModelMultipleChoiceFilter(
        field_name="cluster__name",
        queryset=SlurmCluster.objects.all(),
        distinct=False,
        to_field_name="name",
        label=_("Cluster (name)"),
    )
    user_id = django_filters.ModelChoiceFilter(
        field_name="user",
        queryset=User.objects.all(),
        label=_("User"),
    )
    default_account_id = django_filters.ModelChoiceFilter(
        field_name="default_account",
        queryset=SlurmAccount.objects.all(),
        label=_("Default Account"),
    )
    default_qos_id = django_filters.ModelChoiceFilter(
        field_name="default_qos",
        queryset=SlurmQOS.objects.all(),
        label=_("Default QOS"),
    )

    class Meta:
        model = SlurmUser
        fields = (
            "id",
            "cluster",
            "admin_level",
            "user_id",
            "default_account_id",
            "default_qos_id",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(user__username__icontains=value) | Q(user__email__icontains=value))
