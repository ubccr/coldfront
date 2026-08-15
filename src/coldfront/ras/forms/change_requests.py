# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from crispy_forms.layout import Fieldset
from django import forms
from django.core.validators import EMPTY_VALUES
from django.utils.translation import gettext_lazy as _

from coldfront.core.models import ObjectType
from coldfront.forms import PrimaryModelForm
from coldfront.forms.fields import CommentField
from coldfront.forms.mixins import AllocationExtensionFormMixin
from coldfront.forms.widgets import HTMXSelectWidget
from coldfront.ras.models import Allocation
from coldfront.ras.models.change_requests import (
    AllocationChangeRequest,
)
from coldfront.users.permissions import get_permission_for_model
from coldfront.utils.jsonschema import JSONSchemaProperty


class AllocationChangeRequestForm(AllocationExtensionFormMixin, PrimaryModelForm):
    """Form for creating or editing an AllocationChangeRequest.

    Dynamically adds fields for the proposed changes based on the
    allocation's resource type: extension days, attribute fields from
    the resource schema, and extension fields from registered extensions.
    """

    allocation = forms.ModelChoiceField(
        label=_("Allocation"),
        queryset=Allocation.objects.all(),
        required=True,
        widget=HTMXSelectWidget(),
    )

    class Meta:
        model = AllocationChangeRequest
        fields = [
            "allocation",
            "justification",
            "extension_days",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["allocation"].disabled = True

        # Track dynamically-added field groups
        self.attr_fields = []

        # Determine the allocation to derive change-set fields
        allocation = self._resolve_allocation()
        if allocation is None:
            return

        # --- Attribute fields from resource schema ---
        resource = allocation.resource_object
        if resource and hasattr(resource, "schema") and resource.schema:
            schema = resource.schema
            properties = schema.get("properties", {})

            for attr_name, options in properties.items():
                prop = JSONSchemaProperty(**options)

                # Permission check: skip if user lacks the required action
                if prop.requiredAction:
                    if not getattr(self, "user", None):
                        continue
                    if not getattr(self._meta, "model", None):
                        continue
                    content_type = ObjectType.objects.get_for_model(self._meta.model)
                    perm = get_permission_for_model(content_type.model_class(), prop.requiredAction)
                    if not self.user.has_perms([perm]):
                        continue

                field_name = f"attr_{attr_name}"
                self.attr_fields.append(field_name)
                form_field = prop.to_form_field(attr_name, required=False)
                self.fields[field_name] = form_field

                # Pre-fill with current allocation attribute value only when editing
                if self.instance.pk and allocation.attribute_data and attr_name in allocation.attribute_data:
                    self.fields[field_name].initial = allocation.attribute_data[attr_name]

        # --- Extension fields ---
        self._build_extension_fields(allocation)

        # --- Pre-fill with stored proposed values when editing ---
        if self.instance.pk:
            # Attribute changes
            if self.instance.attribute_changes:
                for attr_name, value in self.instance.attribute_changes.items():
                    field_name = f"attr_{attr_name}"
                    if field_name in self.fields:
                        self.fields[field_name].initial = value

            # Extension changes
            if self.instance.extension_changes:
                for ext_path, values in self.instance.extension_changes.items():
                    # Find the matching model in _extension_field_map
                    for entry in self._extension_field_map:
                        if entry["model_path"] == ext_path:
                            model_name = entry["model"]._meta.model_name
                            for field_name, value in values.items():
                                form_field_name = f"ext_{model_name}_{field_name}"
                                if form_field_name in self.fields:
                                    self.fields[form_field_name].initial = value
                            break

    def _resolve_allocation(self):
        """Resolve the allocation from POST data, initial data, or instance."""
        # From POST data
        allocation_id = self.data.get("allocation") if hasattr(self, "data") and self.data else None
        if allocation_id:
            try:
                return Allocation.objects.get(pk=int(allocation_id))
            except (ValueError, Allocation.DoesNotExist):
                pass

        # From initial data (GET param)
        initial = self.initial.get("allocation") if hasattr(self, "initial") else None
        if initial:
            if isinstance(initial, Allocation):
                return initial
            try:
                return Allocation.objects.get(pk=int(initial))
            except (ValueError, Allocation.DoesNotExist):
                pass

        # From instance (editing an existing change request)
        if self.instance and self.instance.pk and self.instance.allocation_id:
            return self.instance.allocation

        return None

    def _post_clean(self):
        """Build the change-set data from the dynamic fields."""
        result = super()._post_clean()

        # AllocationAttributeChange — collect attr_* fields
        attr_changes = {}
        for name in self.attr_fields:
            key = name[5:]  # Strip "attr_" prefix
            value = self.cleaned_data.get(name)
            if value not in EMPTY_VALUES:
                attr_changes[key] = value
        if attr_changes:
            self.instance.attribute_changes = attr_changes

        # Extension changes — collect ext_* fields
        self.instance.extension_changes = self._collect_extension_data()

        return result

    def save(self, commit=True):
        instance = super().save(commit=False)

        if commit:
            instance.save()

        return instance

    @property
    def fieldsets(self):
        fieldsets = [
            Fieldset(
                _("Change Request"),
                "allocation",
                "justification",
            ),
        ]

        # Extension days fieldset
        if "extension_days" in self.fields:
            fieldsets.append(
                Fieldset(
                    _("Extension"),
                    "extension_days",
                )
            )

        # Attribute fields
        if self.attr_fields:
            fieldsets.append(
                Fieldset(
                    _("Attribute Changes"),
                    *self.attr_fields,
                )
            )

        # Extension fieldsets
        for entry in self._extension_field_map:
            header = _(f"{entry['model']._meta.verbose_name.title()} Changes")
            field_names = [f"ext_{entry['model']._meta.model_name}_{fn}" for fn in entry["field_names"]]
            if field_names:
                fieldsets.append(Fieldset(header, *field_names))

        return fieldsets


class AllocationChangeRequestReviewForm(PrimaryModelForm):
    """Form for reviewing a change request (approve/deny transitions)."""

    comments = CommentField()

    class Meta:
        model = AllocationChangeRequest
        fields = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def fieldsets(self):
        from crispy_forms.layout import Layout

        return Layout("comments")

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
            self._create_comment_entry()
        return instance

    def _create_comment_entry(self):
        comments = self.cleaned_data.get("comments")
        if comments:
            from coldfront.core.choices import CommentKindChoices
            from coldfront.core.models import CommentEntry

            CommentEntry.objects.create(
                assigned_object=self.instance,
                created_by=getattr(self, "user", None),
                kind=CommentKindChoices.KIND_INFO,
                comments=comments,
            )


class AllocationChangeRequestApplyForm(PrimaryModelForm):
    """Confirmation form for the apply transition."""

    comments = CommentField()

    class Meta:
        model = AllocationChangeRequest
        fields = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def fieldsets(self):
        from crispy_forms.layout import Layout

        return Layout("comments")

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
            self._create_comment_entry()
        return instance

    def _create_comment_entry(self):
        comments = self.cleaned_data.get("comments")
        if comments:
            from coldfront.core.choices import CommentKindChoices
            from coldfront.core.models import CommentEntry

            CommentEntry.objects.create(
                assigned_object=self.instance,
                created_by=getattr(self, "user", None),
                kind=CommentKindChoices.KIND_INFO,
                comments=comments,
            )
