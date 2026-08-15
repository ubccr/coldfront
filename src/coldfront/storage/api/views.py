# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from rest_framework.routers import APIRootView

from coldfront.api.viewsets import ColdFrontModelViewSet
from coldfront.storage import filtersets
from coldfront.storage.models import (
    StorageCluster,
    StorageQuota,
    StorageResource,
    StorageSnapshotPolicy,
)

from . import serializers


class StorageRootView(APIRootView):
    """
    Storage API root view
    """

    def get_view_name(self):
        return "Storage"


class StorageSnapshotPolicyViewSet(ColdFrontModelViewSet):
    queryset = StorageSnapshotPolicy.objects.all()
    serializer_class = serializers.StorageSnapshotPolicySerializer
    filterset_class = filtersets.StorageSnapshotPolicyFilterSet


class StorageClusterViewSet(ColdFrontModelViewSet):
    queryset = StorageCluster.objects.all()
    serializer_class = serializers.StorageClusterSerializer
    filterset_class = filtersets.StorageClusterFilterSet


class StorageResourceViewSet(ColdFrontModelViewSet):
    queryset = StorageResource.objects.all()
    serializer_class = serializers.StorageResourceSerializer
    filterset_class = filtersets.StorageResourceFilterSet


class StorageQuotaViewSet(ColdFrontModelViewSet):
    queryset = StorageQuota.objects.all()
    serializer_class = serializers.StorageQuotaSerializer
    filterset_class = filtersets.StorageQuotaFilterSet
