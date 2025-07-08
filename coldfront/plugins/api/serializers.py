# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.contrib.auth import get_user_model
from rest_framework import serializers

from coldfront.core.allocation.models import Allocation, AllocationChangeRequest
from coldfront.core.project.models import Project, ProjectUser
from coldfront.core.resource.models import Resource


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "is_active",
            "is_superuser",
            "is_staff",
            "date_joined",
        )


class ResourceSerializer(serializers.ModelSerializer):
    resource_type = serializers.SlugRelatedField(slug_field="name", read_only=True)

    class Meta:
        model = Resource
        fields = ("id", "resource_type", "name", "description", "is_allocatable")


class AllocationSerializer(serializers.ModelSerializer):
    resource = serializers.ReadOnlyField(source="get_resources_as_string")
    project = serializers.SlugRelatedField(slug_field="title", read_only=True)
    status = serializers.SlugRelatedField(slug_field="name", read_only=True)

    class Meta:
        model = Allocation
        fields = (
            "id",
            "project",
            "resource",
            "status",
        )


class AllocationRequestSerializer(serializers.ModelSerializer):
    project = serializers.SlugRelatedField(slug_field="title", read_only=True)
    resource = serializers.ReadOnlyField(source="get_resources_as_string", read_only=True)
    status = serializers.SlugRelatedField(slug_field="name", read_only=True)
    fulfilled_date = serializers.DateTimeField(read_only=True)
    created_by = serializers.SerializerMethodField(read_only=True)
    fulfilled_by = serializers.SerializerMethodField(read_only=True)
    time_to_fulfillment = serializers.DurationField(read_only=True)

    class Meta:
        model = Allocation
        fields = (
            "id",
            "project",
            "resource",
            "status",
            "created",
            "created_by",
            "fulfilled_date",
            "fulfilled_by",
            "time_to_fulfillment",
        )

    def get_created_by(self, obj):
        historical_record = obj.history.earliest()
        creator = historical_record.history_user if historical_record else None
        if not creator:
            return None
        return historical_record.history_user.username

    def get_fulfilled_by(self, obj):
        historical_records = obj.history.filter(status__name="Active")
        if historical_records:
            user = historical_records.earliest().history_user
            if user:
                return user.username
        return None


class AllocationChangeRequestSerializer(serializers.ModelSerializer):
    allocation = AllocationSerializer(read_only=True)
    status = serializers.SlugRelatedField(slug_field="name", read_only=True)
    created_by = serializers.SerializerMethodField(read_only=True)
    fulfilled_date = serializers.DateTimeField(read_only=True)
    fulfilled_by = serializers.SerializerMethodField(read_only=True)
    time_to_fulfillment = serializers.DurationField(read_only=True)

    class Meta:
        model = AllocationChangeRequest
        fields = (
            "id",
            "allocation",
            "justification",
            "status",
            "created",
            "created_by",
            "fulfilled_date",
            "fulfilled_by",
            "time_to_fulfillment",
        )

    def get_created_by(self, obj):
        historical_record = obj.history.earliest()
        creator = historical_record.history_user if historical_record else None
        if not creator:
            return None
        return historical_record.history_user.username

    def get_fulfilled_by(self, obj):
        if not obj.status.name == "Approved":
            return None
        historical_record = obj.history.latest()
        fulfiller = historical_record.history_user if historical_record else None
        if not fulfiller:
            return None
        return historical_record.history_user.username


class ProjAllocationSerializer(serializers.ModelSerializer):
    resource = serializers.ReadOnlyField(source="get_resources_as_string")
    status = serializers.SlugRelatedField(slug_field="name", read_only=True)

    class Meta:
        model = Allocation
        fields = ("id", "resource", "status")


class ProjectUserSerializer(serializers.ModelSerializer):
    user = serializers.SlugRelatedField(slug_field="username", read_only=True)
    status = serializers.SlugRelatedField(slug_field="name", read_only=True)
    role = serializers.SlugRelatedField(slug_field="name", read_only=True)

    class Meta:
        model = ProjectUser
        fields = ("user", "role", "status")


class ProjectSerializer(serializers.ModelSerializer):
    pi = serializers.SlugRelatedField(slug_field="username", read_only=True)
    status = serializers.SlugRelatedField(slug_field="name", read_only=True)
    project_users = serializers.SerializerMethodField()
    allocations = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ("id", "title", "pi", "status", "project_users", "allocations")

    def get_project_users(self, obj):
        request = self.context.get("request", None)
        if request and request.query_params.get("project_users") in ["true", "True"]:
            return ProjectUserSerializer(obj.projectuser_set, many=True, read_only=True).data
        return None

    def get_allocations(self, obj):
        request = self.context.get("request", None)
        if request and request.query_params.get("allocations") in ["true", "True"]:
            return ProjAllocationSerializer(obj.allocation_set, many=True, read_only=True).data
        return None
