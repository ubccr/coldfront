# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from rest_framework import serializers

from coldfront.api.serializers import PrimaryModelSerializer
from coldfront.ras.models import (
    Allocation,
    AllocationChangeRequest,
)
from coldfront.registry import get_allocation_extensions
from coldfront.users.api.serializers import UserSerializer


class AllocationChangeRequestSerializer(PrimaryModelSerializer):
    allocation = serializers.PrimaryKeyRelatedField(
        queryset=Allocation.objects.all(),
    )
    requested_by = UserSerializer(nested=True)
    reviewer = UserSerializer(nested=True, required=False, allow_null=True, default=None)
    extension_days = serializers.IntegerField(required=False, allow_null=True, default=None)
    attribute_changes = serializers.JSONField(required=False, allow_null=True, default=None)
    extension_changes = serializers.JSONField(required=False, default=dict)

    class Meta:
        model = AllocationChangeRequest
        fields = [
            "id",
            "url",
            "display_url",
            "display",
            "slug",
            "allocation",
            "status",
            "requested_by",
            "reviewer",
            "justification",
            "extension_days",
            "attribute_changes",
            "extension_changes",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
        ]
        brief_fields = ("id", "url", "display", "slug", "status", "allocation")

    def validate(self, attrs):
        """
        Validate extension_changes data.

        Each key must be a registered extension path for the allocation's
        resource type. Values are validated against the extension model's
        field types.
        """
        extension_changes = attrs.get("extension_changes", {})
        if not extension_changes:
            return attrs

        allocation = attrs.get("allocation")
        if allocation is None:
            raise serializers.ValidationError(
                {"allocation": "Allocation must be specified when providing extension changes."}
            )

        resource = allocation.resource_object
        if resource is None:
            raise serializers.ValidationError(
                {"extension_changes": "Allocation has no resource object; extension changes are not supported."}
            )

        resource_path = resource._meta.label_lower
        supported_models = list(get_allocation_extensions(resource_path))

        # Build a mapping from any string form of the path to the model class
        # so users can use "storage.StorageQuota" or "storage.storagequota"
        ext_model_map = {}
        for m in supported_models:
            ext_model_map[m._meta.label_lower] = m
            ext_model_map[f"{m._meta.app_label}.{m._meta.object_name}"] = m

        validated = {}
        for ext_path, values in extension_changes.items():
            model = ext_model_map.get(ext_path)
            if model is None:
                raise serializers.ValidationError(
                    {
                        "extension_changes": {
                            ext_path: (
                                f"Extension model '{ext_path}' is not supported by "
                                f"resource type '{resource.__class__.__name__}'. "
                                f"Supported extensions: {', '.join(sorted(m._meta.label_lower for m in supported_models))}"
                            )
                        }
                    }
                )

            normalized_path = model._meta.label_lower
            validated[normalized_path] = values

            requestable = model.requestable_fields()
            for field_name, value in values.items():
                if field_name not in requestable:
                    raise serializers.ValidationError(
                        {"extension_changes": {ext_path: f"'{field_name}' is not a requestable field."}}
                    )

            validated[ext_path] = values

        attrs["extension_changes"] = validated
        return attrs

    def to_representation(self, instance):
        """
        Override to_representation to include extension_days, attribute_changes,
        and extension_changes with current extension values for context.
        """
        data = super().to_representation(instance)

        requested_fields = self._include_fields if self._include_fields else None

        # Include extension_changes enriched with current extension values
        if requested_fields is None or "extension_changes" in requested_fields:
            data["extension_changes"] = self._serialize_extension_changes(instance)

        return data

    def _serialize_extension_changes(self, instance):
        """
        Enrich extension_changes with current extension values for display.

        Returns a dict mapping each extension path to a dict with:
          - proposed: the proposed values from the change request
          - current: the current values from the live extension instance
        """
        resource = instance.allocation.resource_object
        if resource is None:
            return {}

        resource_path = resource._meta.label_lower
        result = {}

        for model in get_allocation_extensions(resource_path):
            if model is None:
                continue

            ext_path = model._meta.label_lower

            # Get proposed values from the change request JSON
            proposed = instance.extension_changes.get(ext_path, {})

            # Get current values — use snapshot if available (applied), otherwise live
            if instance.snapshot_extension_values:
                current = instance.snapshot_extension_values.get(ext_path, {})
            else:
                current = {}
                try:
                    ext_instance = model.objects.get(allocation=instance.allocation)
                    requestable = model.requestable_fields()
                    for field_name in requestable:
                        value = getattr(ext_instance, field_name, None)
                        if value is not None:
                            current[field_name] = value
                except model.DoesNotExist:
                    pass

            result[ext_path] = {
                "proposed": proposed,
                "current": current,
            }

        return result

    def create(self, validated_data):
        """
        Create an ``AllocationChangeRequest`` with extension_days,
        attribute_changes, and extension_changes.
        """
        allocation = validated_data.pop("allocation")
        validated_data["allocation"] = allocation

        instance = super().create(validated_data)

        return instance
