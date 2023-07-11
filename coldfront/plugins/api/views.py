from rest_framework import viewsets, mixins, permissions
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Q

from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import Resource
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
                    |(
                        Q(allocationuser__user=self.request.user)
                        & Q(allocationuser__status__name='Active')
                    )
                )
            ).distinct().order_by('project')

        return allocations

class ProjectUserViewSet(viewsets.ReadOnlyModelViewSet):
    """Produce a report of users for each project that includes
    name, usage, status, and usage for all allocations they have space on
    """
    serializer_class = serializers.ProjectUserSerializer
