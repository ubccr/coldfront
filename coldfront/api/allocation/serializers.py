from datetime import datetime

from coldfront.api.resource.serializers import ResourceSerializer
from coldfront.core.allocation.models import Allocation, \
    ClusterAccessRequestStatusChoice, ClusterAccessRequest
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

from coldfront.core.user.models import UserProfile


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


class ClusterAccessRequestSerializer(serializers.ModelSerializer):
    """A serializer for the ClusterAccessRequest model."""
    status = serializers.SlugRelatedField(
        slug_field='name',
        queryset=ClusterAccessRequestStatusChoice.objects.all())

    billing_activity = serializers.CharField(source='billing_activity.full_id',
                                             allow_null=True,
                                             required=False,
                                             read_only=True)

    allocation_user = AllocationUserSerializer(read_only=True,
                                               allow_null=True,
                                               required=False)

    cluster_uid = serializers.CharField(required=False)
    username = serializers.CharField(required=False)

    class Meta:
        model = ClusterAccessRequest
        fields = (
            'id', 'status', 'completion_time', 'cluster_uid',
            'username', 'billing_activity', 'allocation_user')
        extra_kwargs = {
            'id': {'read_only': True},
            'completion_time': {'required': False, 'allow_null': True},
            'allocation_user': {'required': True,
                                'allow_null': False,
                                'read_only': True}
        }

    def validate(self, data):
        # If the status is being changed to 'Complete', ensure that a
        # completion_time, username, and cluster_uid are given.
        if 'status' in data and data['status'].name == 'Active':
            messages = []
            for field in ['completion_time', 'username', 'cluster_uid']:
                if (field == 'completion_time' and
                        not isinstance(data.get('completion_time', None), datetime)):
                    messages.append('No completion_time is given.')

                elif (field == 'username' and
                      not isinstance(data.get('username', None), str)):
                    messages.append('No username is given.')

                elif (field == 'cluster_uid' and
                      not isinstance(data.get('cluster_uid', None), str)):
                    messages.append('No cluster_uid is given.')
            if messages:
                raise serializers.ValidationError(' '.join(messages))

        # Ensure the username given is either unique or belongs to the
        # requesting user.
        if 'username' in data:
            username = data.get('username', None)
            queryset = User.objects.filter(username=username)
            if queryset.exists():
                if queryset.first().pk != self.instance.allocation_user.user.pk:
                    message = f'A user with username {username} already exists.'
                    raise serializers.ValidationError(message)

        # Ensure the cluster_uid given is either unique or belongs to the
        # requesting user.
        if 'cluster_uid' in data:
            cluster_uid = data.get('cluster_uid', None)
            queryset = UserProfile.objects.filter(cluster_uid=cluster_uid)
            if queryset.exists():
                if queryset.first().pk != self.instance.allocation_user.user.userprofile.pk:
                    message = f'A user with cluster_uid ' \
                              f'{cluster_uid} already exists.'
                    raise serializers.ValidationError(message)

        return data
