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
            # Distinguish scalar (app.model) from related (app.model.fk) keys
            parts = ext_path.split(".")
            if len(parts) == 3:
                model_path = f"{parts[0]}.{parts[1]}"
                fk_name = parts[2]
            else:
                model_path = ext_path
                fk_name = None

            model = ext_model_map.get(model_path)
            if model is None:
                raise serializers.ValidationError(
                    {
                        "extension_changes": {
                            ext_path: (
                                f"Extension model '{model_path}' is not supported by "
                                f"resource type '{resource.__class__.__name__}'. "
                                f"Supported extensions: {', '.join(sorted(m._meta.label_lower for m in supported_models))}"
                            )
                        }
                    }
                )

            if fk_name is not None:
                # Related-object target: validate against the model's changeable markers
                valid_fields = set()
                for token in model.fields_for_change():
                    if model.is_related_field_token(token):
                        m_fk, m_field = model.parse_related_field_token(token)
                        if m_fk == fk_name:
                            valid_fields.add(m_field)
                if not valid_fields:
                    raise serializers.ValidationError(
                        {"extension_changes": {ext_path: f"'{fk_name}' is not a changeable related field."}}
                    )
                for field_name, value in values.items():
                    if field_name not in valid_fields:
                        raise serializers.ValidationError(
                            {"extension_changes": {ext_path: f"'{field_name}' is not a requestable field."}}
                        )

                # The related target must exist on the extension for this
                # allocation, or the change could not be applied.  Block it
                # here so a doomed request isn't created.
                try:
                    ext_instance = model.objects.get(allocation=allocation)
                    target = getattr(ext_instance, fk_name)
                except model.DoesNotExist:
                    target = None
                if target is None:
                    fk_label = str(model._meta.get_field(fk_name).verbose_name).capitalize()
                    target_model = model._meta.get_field(fk_name).remote_field.model
                    field_label = str(target_model._meta.get_field(field_name).verbose_name).capitalize()
                    raise serializers.ValidationError(
                        {
                            "extension_changes": {
                                ext_path: (
                                    f"No {fk_label} is linked to this allocation yet — "
                                    f"{field_label} cannot be changed until one is set."
                                )
                            }
                        }
                    )

                normalized_path = f"{model._meta.label_lower}.{fk_name}"
                validated[normalized_path] = values
                validated[ext_path] = values
            else:
                # Scalar fields: requestable + changeable are legal on a change request
                changeable = model.fields_for_change()
                for field_name, value in values.items():
                    if field_name not in changeable:
                        raise serializers.ValidationError(
                            {"extension_changes": {ext_path: f"'{field_name}' is not a requestable field."}}
                        )
                normalized_path = model._meta.label_lower
                validated[normalized_path] = values
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

            # --- Scalar fields ---
            proposed = instance.extension_changes.get(ext_path, {})
            if instance.snapshot_extension_values:
                current = instance.snapshot_extension_values.get(ext_path, {})
            else:
                current = {}
                try:
                    ext_instance = model.objects.get(allocation=instance.allocation)
                    for token in model.fields_for_change():
                        if model.is_related_field_token(token):
                            continue
                        value = getattr(ext_instance, token, None)
                        if value is not None:
                            current[token] = value
                except model.DoesNotExist:
                    pass
            result[ext_path] = {"proposed": proposed, "current": current}

            # --- Related-object fields ---
            for token in model.fields_for_change():
                if not model.is_related_field_token(token):
                    continue
                fk_name, target_field = model.parse_related_field_token(token)
                rkey = f"{ext_path}.{fk_name}"
                proposed = instance.extension_changes.get(rkey, {})
                if instance.snapshot_extension_values:
                    current = instance.snapshot_extension_values.get(rkey, {})
                else:
                    current = {}
                    try:
                        ext_instance = model.objects.get(allocation=instance.allocation)
                        target = getattr(ext_instance, fk_name)
                        if target is not None:
                            current[target_field] = getattr(target, target_field)
                    except model.DoesNotExist:
                        pass
                result[rkey] = {"proposed": proposed, "current": current}

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
