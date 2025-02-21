import csv
from datetime import timedelta

from django.contrib.auth import get_user_model

from django.db.models import OuterRef, Subquery, Q, F, ExpressionWrapper, Case, When, Value, fields, DurationField
from django.db.models.functions import Cast
from django.http import HttpResponse
from django_filters import rest_framework as filters
from ifxuser.models import Organization
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.renderers import AdminRenderer, JSONRenderer

from simple_history.utils import get_history_model_for_model

from coldfront.core.utils.common import import_from_settings
from coldfront.core.allocation.models import Allocation, AllocationChangeRequest
from coldfront.core.project.models import Project
from coldfront.core.resource.models import Resource
from coldfront.plugins.api import serializers

UNFULFILLED_ALLOCATION_STATUSES = ['Denied'] + import_from_settings(
    'PENDING_ALLOCATION_STATUSES', ['New', 'In Progress', 'On Hold', 'Pending Activation']
)

class CustomAdminRenderer(AdminRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):

        # Get the count of objects
        count = len(data['results']) if 'results' in data else len(data)

        # Create the count HTML
        count_html = f'<div><strong>Total Objects: {count}</strong></div>'

        # Render the original content
        original_content = super().render(data, accepted_media_type, renderer_context)

        # Ensure original_content is a string
        if isinstance(original_content, bytes):
            original_content = original_content.decode('utf-8')


        # Get the request object
        request = renderer_context.get('request')

        # Generate the CSV export URL
        query_params = request.GET.copy()
        params_present = request.build_absolute_uri(request.path) != request.build_absolute_uri()
        connector = '&' if params_present else '?'
        export_url = f"{request.build_absolute_uri()}{connector}export=csv"

        # Create the button HTML
        button_html = f'''
        <div style="margin: 20px 0;">
            <a href="{export_url}" class="button" style="padding: 10px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 5px;">Export to CSV</a>
        </div>
        '''

        # Insert the count HTML after the docstring and before the results table
        parts = original_content.split('<table', 1)
        content_with_count_and_button = parts[0] + count_html + button_html +'<table' + parts[1]

        return content_with_count_and_button.encode('utf-8')

class ResourceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = serializers.ResourceSerializer
    queryset = Resource.objects.all()


class AllocationFilter(filters.FilterSet):
    '''Filters for AllocationViewSet.
    created_before is the date the request was created before.
    created_after is the date the request was created after.
    '''
    created = filters.DateFromToRangeFilter()

    class Meta:
        model = Allocation
        fields = [
            'created',
        ]


class AllocationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = serializers.AllocationSerializer
    filterset_class = AllocationFilter
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
    created = filters.DateFromToRangeFilter(label='Created Range')
    fulfilled = filters.BooleanFilter(label='Fulfilled', method='filter_fulfilled')
    fulfilled_date = filters.DateFromToRangeFilter(label='Fulfilled Date Range')
    requested_size = filters.NumericRangeFilter(label='Requested Size', field_name='requested_size')
    pi = filters.CharFilter(label='PI', field_name='project__pi__full_name', lookup_expr='icontains')
    project = filters.CharFilter(label='Project', field_name='project__title', lookup_expr='icontains')
    status = filters.CharFilter(label='Status', field_name='status__name', lookup_expr='icontains')
    time_to_fulfillment = filters.NumericRangeFilter(label='Time-to-fulfillment Range', method='filter_time_to_fulfillment')
    o = filters.OrderingFilter(
        fields=(
            ('id', 'id'),
            ('created', 'created'),
            ('project__title', 'project'),
            ('project__pi__full_name', 'pi'),
            ('status__name', 'status'),
            ('quantity', 'requested_size'),
            ('fulfilled_date', 'fulfilled_date'),
            ('time_to_fulfillment', 'time_to_fulfillment'),
        )
    )

    class Meta:
        model = Allocation
        fields = [
            'created',
            'fulfilled',
            'fulfilled_date',
            'pi',
            'requested_size',
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
    - pi: full name of project PI
    - resource: name of allocation's resource
    - tier: storage tier of allocation's resource
    - path: path to the allocation on the resource
    - status: current status of the allocation
    - size: current size of the allocation
    - created: date created
    - created_by: user who submitted the allocation request
    - fulfilled_date: date the allocation's status was first set to "Active"
    - fulfilled_by: user who first set the allocation status to "Active"
    - time_to_fulfillment: time from request creation to time_to_fulfillment displayed as "DAY_INTEGER HH:MM:SS"

    Filters and ordering can be added either by manually defining in the url or by clicking on the "filters" button in the top right corner.

    Filters:
    - created_before/created_after (structure date as 'YYYY-MM-DD')
    - fulfilled (boolean)
        Set to true to return all approved requests, false to return all pending and denied requests.
    - fulfilled_date_before/fulfilled_date_after (structure date as 'YYYY-MM-DD')
    - time_to_fulfillment_max/time_to_fulfillment_min (integer)
        Set to the maximum/minimum number of days between request creation and time_to_fulfillment.
    '''
    serializer_class = serializers.AllocationRequestSerializer
    filter_backends = (filters.DjangoFilterBackend, )
    filterset_class = AllocationRequestFilter
    permission_classes = [IsAuthenticated, IsAdminUser]
    renderer_classes = [CustomAdminRenderer, JSONRenderer]
    csv_filename = 'allocation_requests.csv'

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
        ).filter(earliest_status_name='New')

        allocations = allocations.annotate(
            fulfilled_date=Subquery(fulfilled_date)
        )
        # Use Case and When to handle null fulfilled_date
        allocations = allocations.annotate(
            time_to_fulfillment=Case(
                When(
                    fulfilled_date__isnull=False,
                    then=ExpressionWrapper(
                        (Cast(Subquery(fulfilled_date), fields.DateTimeField()) - F('created')),
                        output_field=DurationField()
                    )
                ),
                default=Value(None),  # If fulfilled_date is null, set time_to_fulfillment to None
                output_field=DurationField()
            )
        )
        return allocations

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        # Check if the export query parameter is present
        if request.GET.get('export') == 'csv':
            return self.export_to_csv(queryset)

        # Otherwise, use the default list implementation
        return super().list(request, *args, **kwargs)

    def export_to_csv(self, queryset):
        # Create the HttpResponse object with CSV header.
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{self.csv_filename}"'

        # Create a CSV writer object
        writer = csv.writer(response)

        serializer = self.get_serializer()
        field_names = [field.label or field_name for field_name, field in serializer.fields.items()]
        # Write the header row
        writer.writerow(field_names)

        # Write data rows
        for item in queryset:
            serializer_instance = self.get_serializer(item)
            row = [serializer_instance.data[field_name] for field_name in serializer.fields.keys()]
            writer.writerow(row)

        return response


class AllocationChangeRequestFilter(filters.FilterSet):
    '''Filters for AllocationChangeRequestViewSet.
    created_before is the date the request was created before.
    created_after is the date the request was created after.
    '''
    created = filters.DateFromToRangeFilter()
    fulfilled = filters.BooleanFilter(label='Fulfilled', method='filter_fulfilled')
    fulfilled_date = filters.DateFromToRangeFilter(label='Fulfilled Date Range')
    pi = filters.CharFilter(label='PI', field_name='allocation__project__pi__full_name', lookup_expr='icontains')
    project = filters.CharFilter(label='Project', field_name='allocation__project__title', lookup_expr='icontains')
    time_to_fulfillment = filters.NumericRangeFilter(label='Time-to-fulfillment Range', method='filter_time_to_fulfillment')
    o = filters.OrderingFilter(
        fields=(
            ('created', 'created'),
            ('id', 'id'),
            ('allocation__id', 'allocation'),
            ('allocation__project__title', 'project'),
            ('allocation__project__pi__full_name', 'pi'),
            ('status__name', 'status'),
            ('fulfilled_date', 'fulfilled_date'),
            ('time_to_fulfillment', 'time_to_fulfillment'),
        )
    )
    class Meta:
        model = AllocationChangeRequest
        fields = [
            'id',
            'created',
            'fulfilled',
            'fulfilled_date',
            'pi',
            'project',
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
    - id: allocationchangerequest id
    - allocation: allocation id
    - project: project title
    - pi: full name of project PI
    - resource: allocation's resource
    - tier: storage tier of allocation's resource
    - justification: justification provided at time of filing
    - status: request status
    - created: date created
    - created_by: user who created the object.
    - fulfilled_date: date the allocationchangerequests's status was first set to "Approved"
    - fulfilled_by: user who last modified an approved object.

    Filters and ordering can be added either by manually defining in the url or by clicking on the "filters" button in the top right corner.

    Filters:
    - created_before/created_after (structure date as 'YYYY-MM-DD')
    - fulfilled (boolean)
        Set to true to return all approved requests, false to return all pending and denied requests.
    - fulfilled_date_before/fulfilled_date_after (structure date as 'YYYY-MM-DD')
    - time_to_fulfillment_max/time_to_fulfillment_min (integer)
        Set to the maximum/minimum number of days between request creation and time_to_fulfillment.
    '''
    serializer_class = serializers.AllocationChangeRequestSerializer
    filter_backends = (filters.DjangoFilterBackend, )
    filterset_class = AllocationChangeRequestFilter
    renderer_classes = [CustomAdminRenderer, JSONRenderer]
    csv_filename = 'allocation_change_requests.csv'

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

        return requests

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        # Check if the export query parameter is present
        if request.GET.get('export') == 'csv':
            return self.export_to_csv(queryset)

        # Otherwise, use the default list implementation
        return super().list(request, *args, **kwargs)

    def export_to_csv(self, queryset):
        # Create the HttpResponse object with CSV header.
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{self.csv_filename}"'

        # Create a CSV writer object
        writer = csv.writer(response)

        serializer = self.get_serializer()
        field_names = [field.label or field_name for field_name, field in serializer.fields.items()]
        # Write the header row
        writer.writerow(field_names)

        # Write data rows
        for item in queryset:
            serializer_instance = self.get_serializer(item)
            row = [serializer_instance.data[field_name] for field_name in serializer.fields.keys()]
            writer.writerow(row)

        return response


class ProjectFilter(filters.FilterSet):
    '''Filters for ProjectViewSet.
    '''
    created = filters.DateFromToRangeFilter()

    class Meta:
        model = Project
        fields = [
            'created',
        ]

class ProjectViewSet(viewsets.ReadOnlyModelViewSet):
    '''
    Query parameters:
    - allocations (default false)
        Show related allocation data.
    - project_users (default false)
        Show related user data.
    - created_before/created_after (structure date as 'YYYY-MM-DD')
    '''
    serializer_class = serializers.ProjectSerializer
    filterset_class = ProjectFilter

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


class OrganizationViewSet(viewsets.ReadOnlyModelViewSet):
    '''Staff and superuser-only view for organization data.'''
    serializer_class = serializers.OrganizationSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        queryset = Organization.objects.all()
        queryset = queryset.annotate(project=F('projectorganization__project__title'))
        return queryset

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
        queryset = get_user_model().objects.all().prefetch_related('useraffiliation_set')
        return queryset
