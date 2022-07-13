import logging

import rest_framework
from django.db import transaction
from django.http import Http404
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework import mixins, status, viewsets

from coldfront.api.allocation.filters import AllocationAttributeFilter, \
    ClusterAccessRequestFilter
from coldfront.api.allocation.filters import AllocationFilter
from coldfront.api.allocation.filters import AllocationUserAttributeFilter
from coldfront.api.allocation.filters import AllocationUserFilter
from coldfront.api.allocation.serializers import AllocationAttributeSerializer, \
    ClusterAccessRequestSerializer
from coldfront.api.allocation.serializers import AllocationSerializer
from coldfront.api.allocation.serializers import AllocationUserAttributeSerializer
from coldfront.api.allocation.serializers import AllocationUserSerializer
from coldfront.api.allocation.serializers import HistoricalAllocationAttributeSerializer
from coldfront.api.allocation.serializers import HistoricalAllocationUserAttributeSerializer
from coldfront.api.permissions import IsAdminUserOrReadOnly
from coldfront.core.allocation.models import Allocation, ClusterAccessRequest
from coldfront.core.allocation.models import AllocationAttribute
from coldfront.core.allocation.models import AllocationUser
from coldfront.core.allocation.models import AllocationUserAttribute
from coldfront.core.allocation.models import HistoricalAllocationAttribute
from coldfront.core.allocation.models import HistoricalAllocationUserAttribute
from coldfront.api.permissions import IsAdminUserOrReadOnly, IsSuperuserOrStaff


authorization_parameter = openapi.Parameter(
    'Authorization',
    openapi.IN_HEADER,
    description=(
        'The authorization token for the requester. The token should be '
        'preceded by "Token " (no quotes).'),
    type=openapi.TYPE_STRING)


class AllocationAttributeViewSet(mixins.ListModelMixin,
                                 mixins.RetrieveModelMixin,
                                 viewsets.GenericViewSet):
    """A ViewSet for the AllocationAttribute model."""

    filterset_class = AllocationAttributeFilter
    permission_classes = [IsAdminUserOrReadOnly]
    serializer_class = AllocationAttributeSerializer

    def get_queryset(self):
        allocation_pk = self.kwargs.get('allocation_pk', None)
        allocation_attributes = AllocationAttribute.objects.all()
        if allocation_pk:
            allocation_attributes = allocation_attributes.filter(
                allocation=allocation_pk)
        return allocation_attributes.order_by('id')


class AllocationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    """A ViewSet for the Allocation model."""

    filterset_class = AllocationFilter
    permission_classes = [IsAdminUserOrReadOnly]
    serializer_class = AllocationSerializer

    def get_queryset(self):
        return Allocation.objects.order_by('id')


class AllocationUserAttributeViewSet(mixins.ListModelMixin,
                                     mixins.RetrieveModelMixin,
                                     viewsets.GenericViewSet):
    """A ViewSet for the AllocationUserAttribute model."""

    filterset_class = AllocationUserAttributeFilter
    permission_classes = [IsAdminUserOrReadOnly]
    serializer_class = AllocationUserAttributeSerializer

    def get_queryset(self):
        allocation_user_pk = self.kwargs.get('allocation_user_pk', None)
        allocation_user_attributes = AllocationUserAttribute.objects.all()
        if allocation_user_pk:
            allocation_user_attributes = allocation_user_attributes.filter(
                allocation_user=allocation_user_pk)
        return allocation_user_attributes.order_by('id')


class AllocationUserViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                            viewsets.GenericViewSet):
    """A ViewSet for the AllocationUser model."""

    filterset_class = AllocationUserFilter
    permission_classes = [IsAdminUserOrReadOnly]
    serializer_class = AllocationUserSerializer

    def get_queryset(self):
        return AllocationUser.objects.order_by('id')


class HistoricalAllocationAttributeViewSet(mixins.ListModelMixin,
                                           mixins.RetrieveModelMixin,
                                           viewsets.GenericViewSet):
    """A ViewSet for the HistoricalAllocationAttribute model."""

    permission_classes = [IsAdminUserOrReadOnly]
    serializer_class = HistoricalAllocationAttributeSerializer

    def get_queryset(self):
        allocation_pk = self.kwargs.get('allocation_pk', None)
        allocation_attributes = HistoricalAllocationAttribute.objects.all()
        if allocation_pk:
            allocation_attributes = allocation_attributes.filter(
                allocation=allocation_pk)
        return allocation_attributes.order_by("-history_date")


class HistoricalAllocationUserAttributeViewSet(mixins.ListModelMixin,
                                               mixins.RetrieveModelMixin,
                                               viewsets.GenericViewSet):
    """A ViewSet for the HistoricalAllocationUserAttribute model."""

    permission_classes = [IsAdminUserOrReadOnly]
    serializer_class = HistoricalAllocationUserAttributeSerializer

    def get_queryset(self):
        allocation_user_pk = self.kwargs.get('allocation_user_pk', None)
        allocation_user_attributes = \
            HistoricalAllocationUserAttribute.objects.all()
        if allocation_user_pk:
            allocation_user_attributes = allocation_user_attributes.filter(
                allocation_user=allocation_user_pk)
        return allocation_user_attributes.order_by("-history_date")


class ClusterAccessRequestViewSet(mixins.ListModelMixin,
                                       mixins.RetrieveModelMixin,
                                       mixins.UpdateModelMixin,
                                       viewsets.GenericViewSet):
    """A ViewSet for the ClusterAccessRequestViewSet model."""

    filterset_class = ClusterAccessRequestFilter
    http_method_names = ['get', 'patch']
    permission_classes = [IsSuperuserOrStaff]
    serializer_class = ClusterAccessRequestSerializer

    def get_queryset(self):
        return ClusterAccessRequest.objects.order_by('id')

    @swagger_auto_schema(
        manual_parameters=[authorization_parameter],
        operation_description=(
                'Updates one or more fields of the ClusterAccessRequest '
                'identified by the given ID.'))
    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        """The method for PATCH (partial update) requests."""
        logger = logging.getLogger(__name__)

        partial = kwargs.pop('partial', False)

        try:
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial)

        except Http404:
            serializer = self.get_serializer(
                data=request.data, partial=partial)

        serializer.is_valid(raise_exception=True)

        try:
            status_name = serializer.validated_data.get('status', None).name
            completion_time = serializer.validated_data.get('completion_time', None)
            runner = \
                ProjectRemovalRequestUpdateRunner(instance)

            if status_name == 'Complete':
                runner.update_request(status_name)
                runner.complete_request(completion_time=completion_time)
                runner.send_emails()
            elif status_name in ['Pending', 'Processing']:
                runner.update_request(status_name)

            success_messages, error_messages = runner.get_messages()

            if error_messages:
                raise Exception(f'Failed to update the status of the removal '
                                f'request {kwargs["pk"]}.')

            return Response(serializer.data,
                            status=rest_framework.status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f'Failed to update the status of the removal '
                             f'request {kwargs["pk"]}.')

        return Response(serializer.errors,
                        status=rest_framework.status.HTTP_500_INTERNAL_SERVER_ERROR)
