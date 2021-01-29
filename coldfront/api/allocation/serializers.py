from coldfront.api.resource.serializers import ResourceSerializer
from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationAttribute
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AllocationAttributeUsage
from coldfront.core.allocation.models import AllocationStatusChoice
from coldfront.core.allocation.models import AllocationUserStatusChoice
from coldfront.core.allocation.models import AllocationUser
from coldfront.core.allocation.models import AllocationUserAttribute
from coldfront.core.allocation.models import AllocationUserAttributeUsage
from coldfront.core.allocation.models import HistoricalAllocationAttribute
from coldfront.core.allocation.models import HistoricalAllocationUserAttribute
from coldfront.core.project.models import Project
from django.contrib.auth.models import User
from rest_framework import serializers


class AllocationAttributeUsageSerializer(serializers.ModelSerializer):
    """A serializer for the AllocationAttributeUsage model."""

    class Meta:
        model = AllocationAttributeUsage
        fields = ('allocation_attribute', 'value',)


class AllocationAttributeSerializer(serializers.ModelSerializer):
    """A serializer for the AllocationAttribute model."""

    allocation_attribute_type = serializers.SlugRelatedField(
        slug_field='name', queryset=AllocationAttributeType.objects.all())
    usage = AllocationAttributeUsageSerializer(
        source='allocationattributeusage')

    class Meta:
        model = AllocationAttribute
        fields = (
            'id', 'allocation_attribute_type', 'allocation', 'value', 'usage',)


class AllocationSerializer(serializers.ModelSerializer):
    """A serializer for the Allocation model."""

    project = serializers.SlugRelatedField(
        slug_field='name', queryset=Project.objects.all())
    resources = ResourceSerializer(many=True)
    status = serializers.SlugRelatedField(
        slug_field='name', queryset=AllocationStatusChoice.objects.all())

    class Meta:
        model = Allocation
        fields = (
            'id', 'project', 'resources', 'status', 'quantity', 'start_date',
            'end_date', 'justification', 'description', 'is_locked',)


class AllocationUserAttributeUsageSerializer(serializers.ModelSerializer):
    """A serializer for the AllocationUserAttributeUsage model."""

    class Meta:
        model = AllocationUserAttributeUsage
        fields = ('allocation_user_attribute', 'value',)


class AllocationUserAttributeSerializer(serializers.ModelSerializer):
    """A serializer for the AllocationUserAttribute model."""

    allocation_attribute_type = serializers.SlugRelatedField(
        slug_field='name', queryset=AllocationAttributeType.objects.all())
    usage = AllocationUserAttributeUsageSerializer(
        source='allocationuserattributeusage')

    class Meta:
        model = AllocationUserAttribute
        fields = (
            'id', 'allocation_attribute_type', 'allocation', 'allocation_user',
            'value', 'usage',)


class AllocationUserSerializer(serializers.ModelSerializer):
    """A serializer for the AllocationUser model."""

    user = serializers.SlugRelatedField(
        slug_field='username', queryset=User.objects.all())
    project = serializers.CharField(source='allocation.project.name')
    status = serializers.SlugRelatedField(
        slug_field='name', queryset=AllocationUserStatusChoice.objects.all())

    class Meta:
        model = AllocationUser
        fields = (
            'id', 'allocation', 'user', 'project', 'status',)


class HistoricalAllocationAttributeSerializer(serializers.ModelSerializer):
    """A serializer for the HistoricalAllocationAttribute model."""

    allocation_attribute_type = serializers.SlugRelatedField(
        slug_field='name', queryset=AllocationAttributeType.objects.all())

    class Meta:
        model = HistoricalAllocationAttribute
        fields = (
            'history_id', 'id', 'value', 'history_date',
            'history_change_reason', 'history_type',
            'allocation_attribute_type', 'allocation', 'history_user',)


class HistoricalAllocationUserAttributeSerializer(serializers.ModelSerializer):
    """A serializer for the HistoricalAllocationUserAttribute model."""

    allocation_attribute_type = serializers.SlugRelatedField(
        slug_field='name', queryset=AllocationAttributeType.objects.all())

    class Meta:
        model = HistoricalAllocationUserAttribute
        fields = (
            'history_id', 'id', 'value', 'history_date',
            'history_change_reason', 'history_type',
            'allocation_attribute_type', 'allocation', 'allocation_user',
            'history_user',)
