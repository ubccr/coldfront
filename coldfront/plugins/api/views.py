from rest_framework import viewsets

from django.db.models import Q
from django.contrib.auth import get_user_model
from django_filters import rest_framework as filters

from coldfront.core.allocation.models import Allocation
from coldfront.core.project.models import Project
from coldfront.core.resource.models import Resource
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

        if not self.request.user.is_superuser or self.request.user.has_perm(
            'allocation.can_view_all_allocations'
        ):
            allocations = allocations.filter(
                Q(project__status__name__in=['New', 'Active']) &
                (
                    (
                        Q(project__projectuser__role__name='Manager')
                        & Q(project__projectuser__user=self.request.user)
                    )
                    | Q(project__pi=self.request.user)
                )
            ).distinct()

        allocations = allocations.order_by('project')

        return allocations


class ProjectViewSet(viewsets.ReadOnlyModelViewSet):
    '''
    Query parameters:
    - allocations (default false)
    - users (default false)
    '''
    serializer_class = serializers.ProjectSerializer

    def get_queryset(self):
        projects = Project.objects.prefetch_related('status')

        if not self.request.user.is_superuser or self.request.user.has_perm(
            'project.can_view_all_projects'
        ):
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

        if self.request.query_params.get('users') == 'true':
            projects = projects.prefetch_related('projectuser_set')

        if self.request.query_params.get('allocations') == 'true':
            projects = projects.prefetch_related('allocation_set')

        return projects.order_by('pi')


class UserFilter(filters.FilterSet):
    is_staff = filters.BooleanFilter()
    is_active = filters.BooleanFilter()
    is_superuser = filters.BooleanFilter()
    username = filters.CharFilter(field_name='username', lookup_expr='exact')

    class Meta:
        model = get_user_model()
        fields = ['is_staff', 'is_active', 'is_superuser', 'username']


class UserViewSet():
    '''
    Filter parameters:
    - username (exact)
    - is_active
    - is_superuser
    - is_staff
    '''
    serializer_class = serializers.UserSerializer
    queryset = get_user_model().objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = UserFilter
