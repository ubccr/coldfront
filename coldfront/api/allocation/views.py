from coldfront.api.allocation.filters import AllocationAttributeFilter
from coldfront.api.allocation.filters import AllocationFilter
from coldfront.api.allocation.filters import AllocationUserAttributeFilter
from coldfront.api.allocation.filters import AllocationUserFilter
from coldfront.api.allocation.serializers import AllocationAttributeSerializer
from coldfront.api.allocation.serializers import AllocationSerializer
from coldfront.api.allocation.serializers import AllocationUserAttributeSerializer
from coldfront.api.allocation.serializers import AllocationUserSerializer
from coldfront.api.allocation.serializers import HistoricalAllocationAttributeSerializer
from coldfront.api.allocation.serializers import HistoricalAllocationUserAttributeSerializer
from coldfront.api.permissions import IsAdminUserOrReadOnly
from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationAttribute
from coldfront.core.allocation.models import AllocationUser
from coldfront.core.allocation.models import AllocationUserAttribute
from coldfront.core.allocation.models import HistoricalAllocationAttribute
from coldfront.core.allocation.models import HistoricalAllocationUserAttribute
from rest_framework import mixins
from rest_framework import viewsets


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
        return allocation_attributes


class AllocationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    """A ViewSet for the Allocation model."""

    filterset_class = AllocationFilter
    permission_classes = [IsAdminUserOrReadOnly]
    serializer_class = AllocationSerializer

    def get_queryset(self):
        return Allocation.objects.all()


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
        return allocation_user_attributes


class AllocationUserViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                            viewsets.GenericViewSet):
    """A ViewSet for the AllocationUser model."""

    filterset_class = AllocationUserFilter
    permission_classes = [IsAdminUserOrReadOnly]
    serializer_class = AllocationUserSerializer

    def get_queryset(self):
        return AllocationUser.objects.all()


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
        return allocation_attributes


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
        return allocation_user_attributes
