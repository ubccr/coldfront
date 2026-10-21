# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from rest_framework import serializers

from coldfront.lib.api.serializers import AllocatableResourceModelSerializer, PrimaryModelSerializer
from coldfront.lib.api.serializers.fields import RelatedObjectCountField
from coldfront.slurm.models import (
    SlurmAccount,
    SlurmAssociation,
    SlurmCluster,
    SlurmPartition,
    SlurmQOS,
    SlurmUser,
)
from coldfront.slurm.parser import format_slurm_time, parse_slurm_time
from coldfront.tenancy.api.serializers.tenants import TenantSerializer
from coldfront.users.api.serializers.nested import NestedGroupSerializer

from .nested import (
    NestedSlurmAccountSerializer,
    NestedSlurmClusterSerializer,
    NestedSlurmQOSSerializer,
)


class SlurmTimeSerializerField(serializers.CharField):
    """DRF field for a SlurmTime model field: canonical string on the wire.

    Reads the SlurmTime attribute (via ``get_attribute``) and renders it with
    ``format_slurm_time``; parses incoming strings with ``parse_slurm_time``.
    """

    def to_representation(self, value):
        if value is None:
            return ""
        return format_slurm_time(value)

    def to_internal_value(self, data):
        if not data:
            return None
        try:
            return parse_slurm_time(data)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))


class SlurmQOSSerializer(PrimaryModelSerializer):
    max_wall_duration_per_job = SlurmTimeSerializerField(required=False, allow_null=True)

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
            "priority_flags",
            "priority_type",
            "priority_decay_half_life",
            "priority_usage_reset_period",
            "enforce_su_limits",
        ]
        brief_fields = ("id", "url", "display", "name", "description", "locked")


class SlurmPartitionSerializer(AllocatableResourceModelSerializer, PrimaryModelSerializer):
    max_time = SlurmTimeSerializerField(required=False, allow_null=True)
    default_time = SlurmTimeSerializerField(required=False, allow_null=True)
    cluster = NestedSlurmClusterSerializer(nested=True)
    allow_qos = NestedSlurmQOSSerializer(nested=True, many=True, required=False)
    deny_qos = NestedSlurmQOSSerializer(nested=True, many=True, required=False)
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
            "priority_tier",
            "max_nodes",
            "max_cpus_per_node",
            "is_default",
            "default_time",
            "state",
            "preempt_mode",
            "def_mem_per_cpu",
            "def_mem_per_node",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
            "schema",
            "max_time",
            "tres_billing_weights",
            "allow_qos",
            "deny_qos",
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
            "service_units",
            "qos_add",
            "qos_remove",
        ]
        brief_fields = ("id", "url", "display", "name", "description")


class SlurmAssociationSerializer(PrimaryModelSerializer):
    max_wall_duration_per_job = SlurmTimeSerializerField(required=False, allow_null=True)
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
