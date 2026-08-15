# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0


from coldfront.api.serializers import WritableNestedSerializer
from coldfront.slurm import models

__all__ = (
    "NestedSlurmClusterSerializer",
    "NestedSlurmPartitionSerializer",
    "NestedSlurmQOSSerializer",
    "NestedSlurmAccountSerializer",
)


class NestedSlurmQOSSerializer(WritableNestedSerializer):
    class Meta:
        model = models.SlurmQOS
        fields = ["id", "url", "display_url", "display", "name"]
        brief_fields = ("id", "url", "display", "name")


class NestedSlurmClusterSerializer(WritableNestedSerializer):
    class Meta:
        model = models.SlurmCluster
        fields = ["id", "url", "display_url", "display", "name"]
        brief_fields = ("id", "url", "display", "name")


class NestedSlurmPartitionSerializer(WritableNestedSerializer):
    class Meta:
        model = models.SlurmPartition
        fields = ["id", "url", "display_url", "display", "name"]
        brief_fields = ("id", "url", "display", "name")


class NestedSlurmAccountSerializer(WritableNestedSerializer):
    class Meta:
        model = models.SlurmAccount
        fields = ["id", "url", "display_url", "display", "name"]
        brief_fields = ("id", "url", "display", "name")
