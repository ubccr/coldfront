from datetime import timedelta

from django.contrib.auth import get_user_model
from ifxuser.models import Organization, UserAffiliation
from rest_framework import serializers

from coldfront.core.resource.models import Resource
from coldfront.core.project.models import Project, ProjectUser
from coldfront.core.allocation.models import Allocation, AllocationChangeRequest
from coldfront.plugins.ifx.models import ProjectOrganization


class UserAffiliationSerializer(serializers.ModelSerializer):
    user = serializers.SlugRelatedField(slug_field='full_name', read_only=True)

    class Meta:
        model = UserAffiliation
        fields = (
            'organization',
            'user',
            'role',
            'active',
        )


class OrganizationSerializer(serializers.ModelSerializer):
    project = serializers.CharField(read_only=True)

    class Meta:
        model = Organization
        fields = (
            'ifxorg',
            'name',
            'rank',
            'org_tree',
            'project'
        )


class UserSerializer(serializers.ModelSerializer):
    primary_affiliation = serializers.SlugRelatedField(slug_field='name', read_only=True)
    affiliations = UserAffiliationSerializer(source='useraffiliation_set', many=True, read_only=True)

    class Meta:
        model = get_user_model()
        fields = (
            'id',
            'username',
            'full_name',
            'is_active',
            'is_superuser',
            'is_staff',
            'date_joined',
            'last_update',
            'primary_affiliation',
            'affiliations',
        )


class ResourceSerializer(serializers.ModelSerializer):
    resource_type = serializers.SlugRelatedField(slug_field='name', read_only=True)

    class Meta:
        model = Resource
        fields = ('id', 'resource_type', 'name', 'description', 'is_allocatable')


class AllocationPctUsageField(serializers.Field):
    def to_representation(self, data):
        if data.usage and float(data.size):
            return round((data.usage / float(data.size) * 100), 2)
        if data.usage == 0:
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


class AllocationRequestSerializer(serializers.ModelSerializer):
    project = serializers.SlugRelatedField(slug_field='title', read_only=True)
    resource = serializers.SlugRelatedField(slug_field='name', read_only=True)
    status = serializers.SlugRelatedField(slug_field='name', read_only=True)
    fulfilled_date = serializers.DateTimeField()
    created_by = serializers.SerializerMethodField()
    fulfilled_by = serializers.SerializerMethodField()
    time_to_fulfillment = serializers.DurationField()

    class Meta:
        model = Allocation
        fields = (
            'id',
            'project',
            'resource',
            'path',
            'status',
            'size',
            'created',
            'created_by',
            'fulfilled_date',
            'fulfilled_by',
            'time_to_fulfillment',
        )

    def get_created_by(self, obj):
        historical_record = obj.history.earliest()
        creator = historical_record.history_user if historical_record else None
        if not creator:
            return None
        return historical_record.history_user.username

    def get_fulfilled_by(self, obj):
        historical_records = obj.history.filter(status__name='Active')
        if historical_records:
            user = historical_records.earliest().history_user
            if user:
                return user.username
        return None


class AllocationChangeRequestSerializer(serializers.ModelSerializer):
    allocation = AllocationSerializer(read_only=True)
    status = serializers.SlugRelatedField(slug_field='name', read_only=True)
    created_by = serializers.SerializerMethodField()
    fulfilled_date = serializers.DateTimeField()
    fulfilled_by = serializers.SerializerMethodField()
    time_to_fulfillment = serializers.DurationField()

    class Meta:
        model = AllocationChangeRequest
        fields = (
            'id',
            'allocation',
            'justification',
            'status',
            'created',
            'created_by',
            'fulfilled_date',
            'fulfilled_by',
            'time_to_fulfillment',
        )

    def get_created_by(self, obj):
        historical_record = obj.history.earliest()
        creator = historical_record.history_user if historical_record else None
        if not creator:
            return None
        return historical_record.history_user.username

    def get_fulfilled_by(self, obj):
        if not obj.status.name == 'Approved':
            return None
        historical_record = obj.history.latest()
        fulfiller = historical_record.history_user if historical_record else None
        if not fulfiller:
            return None
        return historical_record.history_user.username


class ProjAllocationSerializer(serializers.ModelSerializer):
    resource = serializers.ReadOnlyField(source='get_resources_as_string')
    status = serializers.SlugRelatedField(slug_field='name', read_only=True)
    size = serializers.FloatField()

    class Meta:
        model = Allocation
        fields = ('id', 'resource', 'status', 'path', 'size', 'usage')


class ProjectUserSerializer(serializers.ModelSerializer):
    user = serializers.SlugRelatedField(slug_field='full_name', read_only=True)
    status = serializers.SlugRelatedField(slug_field='name', read_only=True)
    role = serializers.SlugRelatedField(slug_field='name', read_only=True)

    class Meta:
        model = ProjectUser
        fields = ('user', 'role', 'status')


class ProjectSerializer(serializers.ModelSerializer):
    pi = serializers.SlugRelatedField(slug_field='full_name', read_only=True)
    status = serializers.SlugRelatedField(slug_field='name', read_only=True)
    project_users = serializers.SerializerMethodField()
    allocations = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ('id', 'title', 'pi', 'status', 'project_users', 'allocations')

    def get_project_users(self, obj):
        request = self.context.get('request', None)
        if request and request.query_params.get('project_users') == 'true':
            return ProjectUserSerializer(obj.projectuser_set, many=True, read_only=True).data
        return None

    def get_allocations(self, obj):
        request = self.context.get('request', None)
        if request and request.query_params.get('allocations') == 'true':
            return ProjAllocationSerializer(obj.allocation_set, many=True, read_only=True).data
        return None
