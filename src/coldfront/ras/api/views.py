# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from rest_framework.routers import APIRootView

from coldfront.api.viewsets import ColdFrontModelViewSet
from coldfront.api.viewsets.mixins import WorkflowViewSetMixin
from coldfront.ras import filtersets
from coldfront.ras.flows import AllocationStatusFlow
from coldfront.ras.models import (
    Allocation,
    AllocationChangeRequest,
    Project,
    ProjectUser,
    Resource,
    ResourceType,
)

from . import serializers


class RASRootView(APIRootView):
    """
    RAS API root view
    """

    def get_view_name(self):
        return "RAS"


#
# Projects
#


class ProjectViewSet(ColdFrontModelViewSet):
    queryset = Project.objects.all()
    serializer_class = serializers.ProjectSerializer
    filterset_class = filtersets.ProjectFilterSet


class ProjectUserViewSet(ColdFrontModelViewSet):
    queryset = ProjectUser.objects.all()
    serializer_class = serializers.ProjectUserSerializer
    filterset_class = filtersets.ProjectUserFilterSet


#
# Resources
#


class ResourceViewSet(ColdFrontModelViewSet):
    queryset = Resource.objects.all()
    serializer_class = serializers.ResourceSerializer
    filterset_class = filtersets.ResourceFilterSet


class ResourceTypeViewSet(ColdFrontModelViewSet):
    queryset = ResourceType.objects.all()
    serializer_class = serializers.ResourceTypeSerializer
    filterset_class = filtersets.ResourceTypeFilterSet


#
# Allocations
#


class AllocationViewSet(WorkflowViewSetMixin, ColdFrontModelViewSet):
    queryset = Allocation.objects.all()
    serializer_class = serializers.AllocationSerializer
    filterset_class = filtersets.AllocationFilterSet
    flow_class = AllocationStatusFlow


#
# Change Requests
#


class AllocationChangeRequestViewSet(ColdFrontModelViewSet):
    queryset = AllocationChangeRequest.objects.all()
    serializer_class = serializers.AllocationChangeRequestSerializer
    filterset_class = filtersets.AllocationChangeRequestFilterSet
