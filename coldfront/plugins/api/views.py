from rest_framework import viewsets

from django.db.models import OuterRef, Subquery, Q
from simple_history.utils import get_history_model_for_model
from django.contrib.auth import get_user_model
from django_filters import rest_framework as filters

from coldfront.core.allocation.models import Allocation, AllocationChangeRequest
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

        if not (self.request.user.is_superuser or self.request.user.has_perm(
            'allocation.can_view_all_allocations'
        )):
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


class AllocationRequestFilter(filters.FilterSet):
    '''Filters for AllocationChangeRequestViewSet.
    created_before is the date the request was created before.
    created_after is the date the request was created after.
    '''
    created_before = filters.DateTimeFilter(field_name='created', lookup_expr='lte')
    created_after = filters.DateTimeFilter(field_name='created', lookup_expr='gte')
    fulfilled = filters.BooleanFilter(method='filter_fulfilled')

    fulfilled_before = filters.DateTimeFilter(method='filter_fulfilled_before')
    fulfilled_after = filters.DateTimeFilter(method='filter_fulfilled_after')

    class Meta:
        model = Allocation
        fields = [
            'created_before',
            'created_after',
            'fulfilled',
            'fulfilled_before',
            'fulfilled_after',
        ]

    def filter_fulfilled_before(self, queryset, name, value):
        return queryset.filter(fulfilled_date__lte=value)

    def filter_fulfilled_after(self, queryset, name, value):
        return queryset.filter(fulfilled_date__gte=value)


class AllocationRequestViewSet(viewsets.ReadOnlyModelViewSet):
    '''Report view on allocations requested through Coldfront.
    Data:
    - id: allocation id
    - project: project name
    - resource: resource name
    - path: path to the allocation on the resource
    - status: current status of the allocation
    - size: current size of the allocation
    - created: date created
    - created_by: user who submitted the allocation request
    - fulfilled_date: date the allocation's status was first set to "Active"
    - fulfilled_by: user who first set the allocation status to "Active"

    Filters:
    - created_before (structure date as 'YYYY-MM-DD')
    - created_after (structure date as 'YYYY-MM-DD')
    - fulfilled (boolean)
        Set to true to return all approved requests, false to return all pending and denied requests.
    - fulfilled_before (structure date as 'YYYY-MM-DD')
    - fulfilled_after (structure date as 'YYYY-MM-DD')

    '''
    serializer_class = serializers.AllocationRequestSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = AllocationRequestFilter

    def get_queryset(self):
        HistoricalAllocation = get_history_model_for_model(Allocation)

        # Subquery to get the earliest historical record for each allocation
        earliest_history = HistoricalAllocation.objects.filter(
            id=OuterRef('pk')
        ).order_by('history_date').values('status__name')[:1]

        fulfilled_date = HistoricalAllocation.objects.filter(
            id=OuterRef('pk'), status__name='Active'
        ).order_by('history_date').values('modified')[:1]

        # Annotate allocations with the status_id of their earliest historical record
        allocations = Allocation.objects.annotate(
            earliest_status_name=Subquery(earliest_history)
        ).filter(earliest_status_name='New').order_by('created')
        allocations = allocations.annotate(
            fulfilled_date=Subquery(fulfilled_date)
        )
        return allocations


class AllocationChangeRequestFilter(filters.FilterSet):
    '''Filters for AllocationChangeRequestViewSet.
    created_before is the date the request was created before.
    created_after is the date the request was created after.
    '''
    created_before = filters.DateTimeFilter(field_name='created', lookup_expr='lte')
    created_after = filters.DateTimeFilter(field_name='created', lookup_expr='gte')
    fulfilled = filters.BooleanFilter(method='filter_fulfilled')

    fulfilled_before = filters.DateTimeFilter(method='filter_fulfilled_before')
    fulfilled_after = filters.DateTimeFilter(method='filter_fulfilled_after')

    class Meta:
        model = AllocationChangeRequest
        fields = [
            'created_before',
            'created_after',
            'fulfilled',
            'fulfilled_before',
            'fulfilled_after',
        ]

    def filter_fulfilled(self, queryset, name, value):
        if value:
            return queryset.filter(status__name='Approved')
        else:
            return queryset.filter(status__name__in=['Pending', 'Denied'])

    def filter_fulfilled_before(self, queryset, name, value):
        return queryset.filter(fulfilled_date__lte=value)

    def filter_fulfilled_after(self, queryset, name, value):
        return queryset.filter(fulfilled_date__gte=value)


class AllocationChangeRequestViewSet(viewsets.ReadOnlyModelViewSet):
    '''
    Data:
    - allocation: allocation object details
    - justification: justification provided at time of filing
    - status: request status
    - created: date created
    - created_by: user who created the object.
    - fulfilled_date: date the allocationchangerequests's status was first set to "Approved"
    - fulfilled_by: user who last modified an approved object.

    Query parameters:
    - created_before (structure date as 'YYYY-MM-DD')
    - created_after (structure date as 'YYYY-MM-DD')
    - fulfilled (boolean)
        Set to true to return all approved requests, false to return all pending and denied requests.
    - fulfilled_before (structure date as 'YYYY-MM-DD')
    - fulfilled_after (structure date as 'YYYY-MM-DD')
    '''
    serializer_class = serializers.AllocationChangeRequestSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = AllocationChangeRequestFilter

    def get_queryset(self):
        requests = AllocationChangeRequest.objects.prefetch_related(
            'allocation', 'allocation__project', 'allocation__project__pi'
        )

        if not (self.request.user.is_superuser):
            requests = requests.filter(
                Q(allocation__project__status__name__in=['New', 'Active']) &
                (
                    (
                        Q(allocation__project__projectuser__role__name='Manager')
                        & Q(allocation__project__projectuser__user=self.request.user)
                    )
                    | Q(allocation__project__pi=self.request.user)
                )
            ).distinct()

        HistoricalAllocationChangeRequest = get_history_model_for_model(
                AllocationChangeRequest
        )

        fulfilled_date = HistoricalAllocationChangeRequest.objects.filter(
            id=OuterRef('pk'), status__name='Approved'
        ).order_by('history_date').values('modified')[:1]

        requests = requests.annotate(
            fulfilled_date=Subquery(fulfilled_date)
        )

        requests = requests.order_by('created')

        return requests


class ProjectViewSet(viewsets.ReadOnlyModelViewSet):
    '''
    Query parameters:
    - allocations (default false)
        Show related allocation data.
    - users (default false)
        Show related user data.
    '''
    serializer_class = serializers.ProjectSerializer

    def get_queryset(self):
        projects = Project.objects.prefetch_related('status')

        if not (self.request.user.is_superuser or self.request.user.has_perm(
            'project.can_view_all_projects'
        )):
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

        if self.request.query_params.get('users') in ['True', 'true']:
            projects = projects.prefetch_related('projectuser_set')

        if self.request.query_params.get('allocations') in ['True', 'true']:
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


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    '''
    Filter parameters:
    - username (exact)
    - is_active
    - is_superuser
    - is_staff
    '''
    serializer_class = serializers.UserSerializer
    queryset = get_user_model().objects.all().prefetch_related('useraffiliation_set')
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = UserFilter
