from rest_framework import viewsets
from django.db.models import Q

from coldfront.core.allocation.models import Allocation
from coldfront.core.resource.models import Resource
from coldfront.core.project.models import Project
from coldfront.plugins.api import serializers


class ResourceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = serializers.ResourceSerializer
    queryset = Resource.objects.all()


class AllocationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = serializers.AllocationSerializer
    # permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    def get_queryset(self):
        allocations = Allocation.objects.prefetch_related(
            'project', 'project__pi', 'status'
        )

        if self.request.user.is_superuser or self.request.user.has_perm(
            'allocation.can_view_all_allocations'
        ):
            allocations = allocations.order_by('project')
        else:
            allocations = allocations.filter(
                Q(project__status__name__in=['New', 'Active']) &
                (
                    (
                        Q(project__projectuser__role__name='Manager')
                        & Q(project__projectuser__user=self.request.user)
                    )
                    | Q(project__pi=self.request.user)
                )
            ).distinct().order_by('project')

        return allocations


class ProjectViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = serializers.ProjectSerializer


    def get_queryset(self):
        projects = Project.objects.prefetch_related('status')

        if self.request.user.is_superuser or self.request.user.has_perm(
            'project.can_view_all_projects'
        ):
            projects = projects.order_by('pi')
        else:
            projects = projects.filter(
                Q(status__name__in=['New', 'Active']) &
                (
                    (
                        Q(projectuser__role__name='Manager')
                        & Q(projectuser__user=self.request.user)
                    )
                    | Q(pi=self.request.user)
                )
            ).distinct().order_by('pi')

        return projects
