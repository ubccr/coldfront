from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import OuterRef, Subquery, Q, F, ExpressionWrapper, fields
from django.db.models.functions import Cast
from django_filters import rest_framework as filters
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from simple_history.utils import get_history_model_for_model

from coldfront.core.utils.common import import_from_settings
from coldfront.core.allocation.models import Allocation, AllocationChangeRequest
from coldfront.core.project.models import Project
from coldfront.core.resource.models import Resource
from coldfront.plugins.api import serializers

UNFULFILLED_ALLOCATION_STATUSES = ['Denied'] + import_from_settings(
    'PENDING_ALLOCATION_STATUSES', ['New', 'In Progress', 'On Hold', 'Pending Activation']
)

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
                        Q(project__projectuser__role__name__contains='Manager')
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
    created = filters.DateFromToRangeFilter()
    fulfilled = filters.BooleanFilter(method='filter_fulfilled')
    fulfilled_date = filters.DateFromToRangeFilter()
    time_to_fulfillment = filters.NumericRangeFilter(method='filter_time_to_fulfillment')

    class Meta:
        model = Allocation
        fields = [
            'created',
            'fulfilled',
            'fulfilled_date',
            'time_to_fulfillment',
        ]

    def filter_fulfilled(self, queryset, name, value):
        if value:
            return queryset.filter(status__name='Approved')
        else:
            return queryset.filter(status__name__in=UNFULFILLED_ALLOCATION_STATUSES)

    def filter_time_to_fulfillment(self, queryset, name, value):
        if value.start is not None:
            queryset = queryset.filter(
                time_to_fulfillment__gte=timedelta(days=int(value.start))
            )
        if value.stop is not None:
            queryset = queryset.filter(
                time_to_fulfillment__lte=timedelta(days=int(value.stop))
            )
        return queryset


class AllocationRequestViewSet(viewsets.ReadOnlyModelViewSet):
    '''Report view on allocations requested through Coldfront.
    Data:
    - id: allocation id
    - project: project name
    - resource: resource name
    - status: current status of the allocation
    - created: date created
    - created_by: user who submitted the allocation request
    - fulfilled_date: date the allocation's status was first set to "Active"
    - fulfilled_by: user who first set the allocation status to "Active"
    - time_to_fulfillment: time between request creation and time_to_fulfillment
        displayed as "DAY_INTEGER HH:MM:SS"

    Filters:
    - created_before/created_after (structure date as 'YYYY-MM-DD')
    - fulfilled (boolean)
        Set to true to return all approved requests, false to return all pending and denied requests.
    - fulfilled_date_before/fulfilled_date_after (structure date as 'YYYY-MM-DD')
    - time_to_fulfillment_max/time_to_fulfillment_min (integer)
        Set to the maximum/minimum number of days between request creation and time_to_fulfillment.
    '''
    serializer_class = serializers.AllocationRequestSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = AllocationRequestFilter
    permission_classes = [IsAuthenticated, IsAdminUser]

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

        allocations = allocations.annotate(
            time_to_fulfillment=ExpressionWrapper(
                (Cast(Subquery(fulfilled_date), fields.DateTimeField()) - F('created')),
                output_field=fields.DurationField()
            )
        )
        return allocations


class AllocationChangeRequestFilter(filters.FilterSet):
    '''Filters for AllocationChangeRequestViewSet.
    created_before is the date the request was created before.
    created_after is the date the request was created after.
    '''
    created = filters.DateFromToRangeFilter()
    fulfilled = filters.BooleanFilter(method='filter_fulfilled')
    fulfilled_date = filters.DateFromToRangeFilter()
    time_to_fulfillment = filters.NumericRangeFilter(method='filter_time_to_fulfillment')

    class Meta:
        model = AllocationChangeRequest
        fields = [
            'created',
            'fulfilled',
            'fulfilled_date',
            'time_to_fulfillment',
        ]

    def filter_fulfilled(self, queryset, name, value):
        if value:
            return queryset.filter(status__name='Approved')
        else:
            return queryset.filter(status__name__in=['Pending', 'Denied'])

    def filter_time_to_fulfillment(self, queryset, name, value):
        if value.start is not None:
            queryset = queryset.filter(
                time_to_fulfillment__gte=timedelta(days=int(value.start))
            )
        if value.stop is not None:
            queryset = queryset.filter(
                time_to_fulfillment__lte=timedelta(days=int(value.stop))
            )
        return queryset


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
    - created_before/created_after (structure date as 'YYYY-MM-DD')
    - fulfilled (boolean)
        Set to true to return all approved requests, false to return all pending and denied requests.
    - fulfilled_date_before/fulfilled_date_after (structure date as 'YYYY-MM-DD')
    - time_to_fulfillment_max/time_to_fulfillment_min (integer)
        Set to the maximum/minimum number of days between request creation and time_to_fulfillment.
    '''
    serializer_class = serializers.AllocationChangeRequestSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = AllocationChangeRequestFilter

    def get_queryset(self):
        requests = AllocationChangeRequest.objects.prefetch_related(
            'allocation', 'allocation__project', 'allocation__project__pi'
        )

        if not (self.request.user.is_superuser or self.request.user.is_staff):
            requests = requests.filter(
                Q(allocation__project__status__name__in=['New', 'Active']) &
                (
                    (
                        Q(allocation__project__projectuser__role__name__contains='Manager')
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

        requests = requests.annotate(fulfilled_date=Subquery(fulfilled_date))

        requests = requests.annotate(
            time_to_fulfillment=ExpressionWrapper(
                (Cast(Subquery(fulfilled_date), fields.DateTimeField()) - F('created')),
                output_field=fields.DurationField()
            )
        )
        requests = requests.order_by('created')

        return requests


class ProjectViewSet(viewsets.ReadOnlyModelViewSet):
    '''
    Query parameters:
    - allocations (default false)
        Show related allocation data.
    - project_users (default false)
        Show related user data.
    '''
    serializer_class = serializers.ProjectSerializer

    def get_queryset(self):
        projects = Project.objects.prefetch_related('status')

        if not (
            self.request.user.is_superuser
            or self.request.user.is_staff
            or self.request.user.has_perm('project.can_view_all_projects')
        ):
            projects = projects.filter(
                Q(status__name__in=['New', 'Active']) &
                (
                    (
                        Q(projectuser__role__name__contains='Manager')
                        & Q(projectuser__user=self.request.user)
                    )
                    | Q(pi=self.request.user)
                )
            ).distinct().order_by('pi')

        if self.request.query_params.get('project_users') in ['True', 'true']:
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
    '''Staff and superuser-only view for user data.
    Filter parameters:
    - username (exact)
    - is_active
    - is_superuser
    - is_staff
    '''
    serializer_class = serializers.UserSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = UserFilter
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        queryset = get_user_model().objects.all()
        return queryset
