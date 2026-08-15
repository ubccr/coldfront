# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.http import HttpResponse
from rest_framework.decorators import action
from rest_framework.routers import APIRootView

from coldfront.api.viewsets import ColdFrontModelViewSet
from coldfront.slurm import filtersets
from coldfront.slurm.dump import generate_cluster_dump
from coldfront.slurm.models import (
    SlurmAccount,
    SlurmAssociation,
    SlurmCluster,
    SlurmPartition,
    SlurmQOS,
    SlurmUser,
)

from . import serializers


class SlurmRootView(APIRootView):
    """
    Slurm API root view
    """

    def get_view_name(self):
        return "Slurm"


class SlurmQOSViewSet(ColdFrontModelViewSet):
    queryset = SlurmQOS.objects.all()
    serializer_class = serializers.SlurmQOSSerializer
    filterset_class = filtersets.SlurmQOSFilterSet


class SlurmClusterViewSet(ColdFrontModelViewSet):
    queryset = SlurmCluster.objects.all()
    serializer_class = serializers.SlurmClusterSerializer
    filterset_class = filtersets.SlurmClusterFilterSet

    @action(detail=True, methods=["get"], url_path="dump")
    def dump(self, request, pk=None):
        """
        Return the Slurm dump for this cluster as a text file.
        """
        cluster = self.get_object()
        dump_content = generate_cluster_dump(cluster)
        response = HttpResponse(dump_content, content_type="text/plain")
        filename = f"slurm_dump_{cluster.name}.txt"
        response["Content-Disposition"] = f"attachment; filename={filename}"
        return response


class SlurmPartitionViewSet(ColdFrontModelViewSet):
    queryset = SlurmPartition.objects.all()
    serializer_class = serializers.SlurmPartitionSerializer
    filterset_class = filtersets.SlurmPartitionFilterSet


class SlurmAccountViewSet(ColdFrontModelViewSet):
    queryset = SlurmAccount.objects.all()
    serializer_class = serializers.SlurmAccountSerializer
    filterset_class = filtersets.SlurmAccountFilterSet


class SlurmAssociationViewSet(ColdFrontModelViewSet):
    queryset = SlurmAssociation.objects.all()
    serializer_class = serializers.SlurmAssociationSerializer
    filterset_class = filtersets.SlurmAssociationFilterSet


class SlurmUserViewSet(ColdFrontModelViewSet):
    queryset = SlurmUser.objects.all()
    serializer_class = serializers.SlurmUserSerializer
    filterset_class = filtersets.SlurmUserFilterSet
