# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from coldfront.api.serializers import AllocatableResourceModelSerializer, PrimaryModelSerializer
from coldfront.api.serializers.fields import RelatedObjectCountField
from coldfront.slurm.models import (
    SlurmAccount,
    SlurmAssociation,
    SlurmCluster,
    SlurmPartition,
    SlurmQOS,
    SlurmUser,
)
from coldfront.tenancy.api.serializers.tenants import TenantSerializer
from coldfront.users.api.serializers.nested import NestedGroupSerializer

from .nested import (
    NestedSlurmAccountSerializer,
    NestedSlurmClusterSerializer,
    NestedSlurmQOSSerializer,
)


class SlurmQOSSerializer(PrimaryModelSerializer):
    class Meta:
        model = SlurmQOS
        fields = [
            "id",
            "url",
            "display_url",
            "display",
            "name",
            "description",
            "priority",
            "max_submit_jobs_per_user",
            "max_jobs_per_user",
            "max_submit_jobs_per_account",
            "max_jobs_per_account",
            "max_wall_duration_per_job",
            "limit_factor",
            "grace_time",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
        ]
        brief_fields = ("id", "url", "display", "name", "description")


class SlurmClusterSerializer(AllocatableResourceModelSerializer, PrimaryModelSerializer):
    tenant = TenantSerializer(nested=True, required=False, allow_null=True, default=None)
    default_qos = NestedSlurmQOSSerializer(nested=True, required=False, allow_null=True, default=None)
    qos_list = NestedSlurmQOSSerializer(nested=True, many=True, required=False)
    partition_count = RelatedObjectCountField("partitions")

    class Meta:
        model = SlurmCluster
        fields = [
            "id",
            "url",
            "display_url",
            "display",
            "name",
            "tenant",
            "description",
            "locked",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
            "partition_count",
            "schema",
            "default_qos",
            "qos_list",
            "fairshare",
            "features",
            "classification",
        ]
        brief_fields = ("id", "url", "display", "name", "description", "locked")


class SlurmPartitionSerializer(AllocatableResourceModelSerializer, PrimaryModelSerializer):
    cluster = NestedSlurmClusterSerializer(nested=True)
    allow_qos = NestedSlurmQOSSerializer(nested=True, many=True, required=False)
    qos = NestedSlurmQOSSerializer(nested=True, required=False, allow_null=True, default=None)
    allow_groups = NestedGroupSerializer(nested=True, many=True, required=False)
    allow_accounts = NestedSlurmAccountSerializer(nested=True, many=True, required=False)

    class Meta:
        model = SlurmPartition
        fields = [
            "id",
            "url",
            "display_url",
            "display",
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
            "custom_fields",
            "created",
            "last_updated",
            "schema",
            "max_jobs",
            "max_submit_jobs",
            "max_tres_per_job",
            "max_tres_per_node",
            "max_tres_mins_per_job",
            "max_wall_duration_per_job",
            "fairshare",
            "allow_qos",
            "qos",
            "allow_groups",
            "allow_accounts",
        ]
        brief_fields = (
            "id",
            "url",
            "display",
            "name",
            "slug",
            "description",
            "locked",
            "nodes",
            "priority",
            "is_default",
            "state",
        )


class SlurmAccountSerializer(PrimaryModelSerializer):
    cluster = NestedSlurmClusterSerializer(nested=True)
    qos_add = NestedSlurmQOSSerializer(nested=True, many=True, required=False)
    qos_remove = NestedSlurmQOSSerializer(nested=True, many=True, required=False)

    class Meta:
        model = SlurmAccount
        fields = [
            "id",
            "url",
            "display_url",
            "display",
            "cluster",
            "name",
            "description",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
            "fairshare",
            "qos_add",
            "qos_remove",
        ]
        brief_fields = ("id", "url", "display", "name", "description")


class SlurmAssociationSerializer(PrimaryModelSerializer):
    slurm_account = NestedSlurmAccountSerializer(nested=True, required=False, allow_null=True, default=None)
    parent = NestedSlurmAccountSerializer(nested=True, required=False, allow_null=True, default=None)
    default_qos = NestedSlurmQOSSerializer(nested=True, required=False, allow_null=True, default=None)

    class Meta:
        model = SlurmAssociation
        fields = [
            "id",
            "url",
            "display_url",
            "display",
            "allocation",
            "slurm_account",
            "parent",
            "default_qos",
            "fairshare",
            "max_jobs",
            "max_submit_jobs",
            "max_tres_per_job",
            "max_tres_mins_per_job",
            "max_wall_duration_per_job",
            "qos_add",
            "qos_remove",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
        ]
        brief_fields = ("id", "url", "display", "slurm_account", "fairshare")


class SlurmUserSerializer(PrimaryModelSerializer):
    cluster = NestedSlurmClusterSerializer(nested=True)
    default_account = NestedSlurmAccountSerializer(nested=True, required=False, allow_null=True, default=None)
    default_qos = NestedSlurmQOSSerializer(nested=True, required=False, allow_null=True, default=None)

    class Meta:
        model = SlurmUser
        fields = [
            "id",
            "url",
            "display_url",
            "display",
            "cluster",
            "user",
            "default_account",
            "default_wckey",
            "default_qos",
            "admin_level",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
        ]
        brief_fields = ("id", "url", "display", "user", "cluster", "default_account", "admin_level")
