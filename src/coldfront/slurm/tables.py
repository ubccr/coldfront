# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import django_tables2 as tables
from django.utils.translation import gettext_lazy as _

from coldfront.slurm.models import (
    SlurmAccount,
    SlurmAccountUsage,
    SlurmAssociation,
    SlurmCluster,
    SlurmPartition,
    SlurmQOS,
    SlurmUser,
)
from coldfront.tables import PrimaryModelTable, columns
from coldfront.tenancy.tables.columns import TenancyColumnsMixin


class SlurmQOSTable(PrimaryModelTable):
    name = tables.Column(
        verbose_name=_("Name"),
        linkify=True,
    )
    tags = columns.TagColumn(
        url_name="slurm:slurmqos_list",
    )

    class Meta(PrimaryModelTable.Meta):
        model = SlurmQOS
        fields = (
            "pk",
            "id",
            "name",
            "description",
            "tags",
            "created",
            "last_updated",
        )
        default_columns = ("pk", "name", "description")


class SlurmClusterTable(TenancyColumnsMixin, PrimaryModelTable):
    name = tables.Column(
        verbose_name=_("Name"),
        linkify=True,
    )
    partition_count = columns.LinkedCountColumn(
        viewname="slurm:slurmpartition_list",
        url_params={"cluster_id": "pk"},
        verbose_name=_("Partition Count"),
    )
    tags = columns.TagColumn(
        url_name="slurm:slurmcluster_list",
    )

    class Meta(PrimaryModelTable.Meta):
        model = SlurmCluster
        fields = (
            "pk",
            "id",
            "name",
            "description",
            "tenant",
            "locked",
            "partition_count",
            "default_tres_billing_weights",
            "priority_flags",
            "priority_type",
            "priority_decay_half_life",
            "priority_usage_reset_period",
            "enforce_su_limits",
            "tags",
            "created",
            "last_updated",
        )
        default_columns = ("pk", "name", "description", "partition_count", "locked")


class SlurmPartitionTable(PrimaryModelTable):
    name = tables.Column(
        verbose_name=_("Name"),
        linkify=True,
    )
    cluster = columns.ColoredLabelColumn(
        verbose_name=_("Cluster"),
        linkify=True,
    )
    tags = columns.TagColumn(
        url_name="slurm:slurmpartition_list",
    )

    class Meta(PrimaryModelTable.Meta):
        model = SlurmPartition
        fields = (
            "pk",
            "id",
            "cluster",
            "name",
            "slug",
            "description",
            "locked",
            "nodes",
            "priority",
            "is_default",
            "default_time",
            "state",
            "preempt_mode",
            "def_mem_per_cpu",
            "tres_billing_weights",
            "tags",
            "created",
            "last_updated",
        )
        default_columns = ("pk", "name", "cluster", "description", "locked")


class SlurmAccountTable(PrimaryModelTable):
    name = tables.Column(
        verbose_name=_("Name"),
        linkify=True,
    )
    cluster = columns.ColoredLabelColumn(
        verbose_name=_("Cluster"),
    )
    service_units = tables.Column(
        verbose_name=_("Service Units"),
    )
    consumed = tables.Column(
        verbose_name=_("Consumed"),
    )
    remaining = tables.Column(
        verbose_name=_("Remaining"),
        orderable=False,
        empty_values=(),
    )
    tags = columns.TagColumn(
        url_name="slurm:slurmaccount_list",
    )

    def render_consumed(self, record, value):
        """Return the annotated consumed total (None on unannotated querysets)."""
        return value

    def render_remaining(self, record, value):
        """Grant minus consumed; ``—`` when no grant is set."""
        grant = record.service_units
        if grant is None:
            return "—"
        consumed = getattr(record, "consumed", None) or 0
        return grant - consumed

    class Meta(PrimaryModelTable.Meta):
        model = SlurmAccount
        fields = (
            "pk",
            "id",
            "cluster",
            "name",
            "description",
            "service_units",
            "consumed",
            "remaining",
            "tags",
            "created",
            "last_updated",
        )
        default_columns = ("pk", "name", "cluster", "description")


class SlurmAccountUsageTable(PrimaryModelTable):
    actions = columns.ActionsColumn(actions=())
    cluster = tables.Column(
        verbose_name=_("Cluster"),
        linkify=True,
    )
    account = tables.Column(
        verbose_name=_("Account"),
        linkify=True,
    )
    period_start = columns.DateColumn(
        verbose_name=_("Day"),
    )

    class Meta(PrimaryModelTable.Meta):
        model = SlurmAccountUsage
        fields = (
            "pk",
            "cluster",
            "account",
            "period_start",
            "period_end",
            "billing_units_consumed",
            "billing_units_completed",
            "walltime_sec_consumed",
            "walltime_sec_completed",
            "node_hours_consumed",
            "job_count_consumed",
            "job_count_completed",
            "node_hours_by_partition",
            "billing_by_qos",
        )
        default_columns = (
            "pk",
            "cluster",
            "account",
            "period_start",
            "billing_units_consumed",
            "billing_units_completed",
            "node_hours_consumed",
            "job_count_consumed",
        )


class SlurmAssociationTable(PrimaryModelTable):
    allocation = tables.Column(
        linkify=("slurm:slurmassociation", {"pk": tables.A("id")}),
        verbose_name=_("Allocation"),
    )
    slurm_account = columns.ColoredLabelColumn(
        verbose_name=_("Slurm Account"),
    )
    resource_object = tables.Column(
        verbose_name=_("Resource"),
        linkify=True,
        accessor=tables.A("allocation__resource_object"),
    )
    tags = columns.TagColumn(
        url_name="slurm:slurmassociation_list",
    )

    class Meta(PrimaryModelTable.Meta):
        model = SlurmAssociation
        fields = (
            "pk",
            "id",
            "allocation",
            "slurm_account",
            "resource_object",
            "fairshare",
            "tags",
            "created",
            "last_updated",
        )
        default_columns = ("pk", "allocation", "slurm_account", "resource_object", "fairshare")


class SlurmUserTable(PrimaryModelTable):
    user = tables.Column(
        linkify=("slurm:slurmuser", {"pk": tables.A("id")}),
        verbose_name=_("User"),
    )

    cluster = columns.ColoredLabelColumn(
        verbose_name=_("Cluster"),
    )
    default_account = columns.ColoredLabelColumn(
        verbose_name=_("Default Account"),
    )
    tags = columns.TagColumn(
        url_name="slurm:slurmuser_list",
    )

    class Meta(PrimaryModelTable.Meta):
        model = SlurmUser
        fields = (
            "pk",
            "id",
            "user",
            "cluster",
            "default_account",
            "admin_level",
            "tags",
            "created",
            "last_updated",
        )
        default_columns = ("pk", "user", "cluster", "default_account", "admin_level")
