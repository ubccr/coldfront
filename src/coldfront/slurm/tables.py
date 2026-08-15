# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import django_tables2 as tables
from django.utils.translation import gettext_lazy as _

from coldfront.slurm.models import (
    SlurmAccount,
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
    tags = columns.TagColumn(
        url_name="slurm:slurmaccount_list",
    )

    class Meta(PrimaryModelTable.Meta):
        model = SlurmAccount
        fields = (
            "pk",
            "id",
            "cluster",
            "name",
            "description",
            "tags",
            "created",
            "last_updated",
        )
        default_columns = ("pk", "name", "cluster", "description")


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
