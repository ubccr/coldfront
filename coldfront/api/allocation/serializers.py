from coldfront.api.resource.serializers import ResourceSerializer
from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationAttribute
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AllocationAttributeUsage
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

    id = serializers.ReadOnlyField()

    class Meta:
        model = AllocationAttributeUsage
        fields = '__all__'


class AllocationAttributeSerializer(serializers.ModelSerializer):
    """A serializer for the AllocationAttribute model."""

    id = serializers.ReadOnlyField()
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

    id = serializers.ReadOnlyField()
    project = serializers.SlugRelatedField(
        slug_field='name', queryset=Project.objects.all())
    resources = ResourceSerializer(many=True)
    attributes = AllocationAttributeSerializer(
        source='allocationattribute_set', many=True)

    class Meta:
        model = Allocation
        fields = (
            'id', 'project', 'resources', 'status', 'quantity', 'start_date',
            'end_date', 'justification', 'description', 'is_locked',
            'attributes',)


class AllocationUserAttributeUsageSerializer(serializers.ModelSerializer):
    """A serializer for the AllocationUserAttributeUsage model."""

    id = serializers.ReadOnlyField()

    class Meta:
        model = AllocationUserAttributeUsage
        fields = '__all__'


class AllocationUserAttributeSerializer(serializers.ModelSerializer):
    """A serializer for the AllocationUserAttribute model."""

    id = serializers.ReadOnlyField()
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

    id = serializers.ReadOnlyField()
    user = serializers.SlugRelatedField(
        slug_field='username', queryset=User.objects.all())
    project = serializers.CharField(source='allocation.project.name')
    attributes = AllocationUserAttributeSerializer(
        source='allocationuserattribute_set', many=True)

    class Meta:
        model = AllocationUser
        fields = (
            'id', 'allocation', 'user', 'project', 'status', 'attributes',)


class HistoricalAllocationAttributeSerializer(serializers.ModelSerializer):
    """A serializer for the HistoricalAllocationAttribute model."""

    id = serializers.ReadOnlyField()

    class Meta:
        model = HistoricalAllocationAttribute
        fields = '__all__'


class HistoricalAllocationUserAttributeSerializer(serializers.ModelSerializer):
    """A serializer for the HistoricalAllocationUserAttribute model."""

    id = serializers.ReadOnlyField()

    class Meta:
        model = HistoricalAllocationUserAttribute
        fields = '__all__'
