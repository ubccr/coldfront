from rest_framework import serializers

from django.contrib.auth import get_user_model

from coldfront.core.allocation.models import Allocation, AllocationStatusChoice
from coldfront.core.project.models import Project, ProjectStatusChoice
from coldfront.core.resource.models import Resource


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ('id', 'full_name')


class ProjectSerializer(serializers.ModelSerializer):
    pi = serializers.SlugRelatedField(slug_field='full_name', read_only=True)
    status = serializers.SlugRelatedField(slug_field='name', read_only=True)

    class Meta:
        model = Project
        fields = ('id', 'title', 'pi', 'status')


class ResourceSerializer(serializers.ModelSerializer):
    resource_type = serializers.SlugRelatedField(slug_field='name', read_only=True)

    class Meta:
        model = Resource
        fields = '__all__'


class AllocationPctUsageField(serializers.Field):
    def to_representation(self, data):
        if data.usage and float(data.size):
            return round((data.usage / float(data.size) * 100), 2)
        elif data.usage == 0:
            return 0
        return None


class AllocationSerializer(serializers.ModelSerializer):
    resource = serializers.ReadOnlyField(source='get_resources_as_string')
    project = serializers.SlugRelatedField(slug_field='title', read_only=True)
    status = serializers.SlugRelatedField(slug_field='name', read_only=True)
    size = serializers.FloatField()
    pct_full = AllocationPctUsageField(source='*')

    class Meta:
        model = Allocation
        fields = (
            'id',
            'project',
            'resource',
            'status',
            'path',
            'size',
            'usage',
            'pct_full',
            'cost',
        )
