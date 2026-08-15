# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django import forms
from django.utils.translation import gettext_lazy as _

from coldfront.core.choices import CustomFieldUIEditableChoices
from coldfront.core.models import ObjectType, Tag
from coldfront.forms.fields import CommentField, DynamicModelChoiceField, DynamicModelMultipleChoiceField, JSONField
from coldfront.forms.mixins import ChangelogMessageMixin, CustomFieldsMixin, HorizontalFormMixin
from coldfront.tenancy.models import Tenant, TenantGroup


class BulkEditForm(forms.Form):
    """
    Provides bulk edit support for objects.

    Attributes:
        nullable_fields: A list of field names indicating which fields support being set to null/empty
    """

    nullable_fields = ()


class TenancyBulkEditForm(forms.Form):
    """
    Mixin for bulk edit forms that adds tenant fields.

    Includes tenant_group and tenant fields, both nullable for bulk editing.
    """

    tenant_group = DynamicModelChoiceField(
        label=_("Tenant group"),
        queryset=TenantGroup.objects.all(),
        required=False,
        null_option="None",
        initial_params={"tenants": "$tenant"},
    )
    tenant = DynamicModelChoiceField(
        label=_("Tenant"),
        queryset=Tenant.objects.all(),
        required=False,
        query_params={"group_id": "$tenant_group"},
    )


class ColdFrontModelBulkEditForm(HorizontalFormMixin, ChangelogMessageMixin, CustomFieldsMixin, BulkEditForm):
    """
    Base form for modifying multiple ColdFront objects (of the same type) in bulk via the UI.
    Adds support for custom fields and adding/removing tags.

    Attributes:
        fieldsets: An iterable of two-tuples which define a heading and field set to display per section of
            the rendered form (optional). If not defined, all fields will be rendered as a single section.
    """

    fieldsets = None

    pk = forms.ModelMultipleChoiceField(
        queryset=None,  # Set from self.model on init
        widget=forms.MultipleHiddenInput,
    )
    add_tags = DynamicModelMultipleChoiceField(
        label=_("Add tags"),
        queryset=Tag.objects.all(),
        required=False,
    )
    remove_tags = DynamicModelMultipleChoiceField(
        label=_("Remove tags"),
        queryset=Tag.objects.all(),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["pk"].queryset = self.model.objects.all()

        # Restrict tag fields by model
        object_type = ObjectType.objects.get_for_model(self.model)
        self.fields["add_tags"].widget.add_query_param("for_object_type_id", object_type.pk)
        self.fields["remove_tags"].widget.add_query_param("for_object_type_id", object_type.pk)

        self._extend_nullable_fields()

    def _get_form_field(self, customfield):
        return customfield.to_form_field(set_initial=False, enforce_required=False)

    def _extend_nullable_fields(self):
        nullable_common_fields = ["tenant_group", "tenant"]
        nullable_custom_fields = [
            name
            for name, customfield in self.custom_fields.items()
            if not customfield.required and customfield.ui_editable == CustomFieldUIEditableChoices.YES
        ]
        self.nullable_fields = (
            *self.nullable_fields,
            *nullable_common_fields,
            *nullable_custom_fields,
        )


class PrimaryModelBulkEditForm(TenancyBulkEditForm, ColdFrontModelBulkEditForm):
    """
    Bulk edit form for models which inherit from PrimaryModel.
    """

    description = forms.CharField(
        label=_("Description"),
        max_length=100,
        required=False,
    )


class OrganizationalModelBulkEditForm(TenancyBulkEditForm, ColdFrontModelBulkEditForm):
    """
    Bulk edit form for models which inherit from OrganizationalModel.
    """

    description = forms.CharField(
        label=_("Description"),
        max_length=200,
        required=False,
    )
    comments = CommentField()


class AllocatableResourceBulkEditForm(forms.Form):
    """
    Mixin for bulk edit forms that adds allocatable resource fields.

    Includes schema and locked fields shared by all AllocatableResourceMixin models.
    """

    locked = forms.BooleanField(
        label=_("Locked"),
        required=False,
        help_text=_("Prevent users from submitting allocations for this resource."),
    )
    schema = JSONField(
        label=_("Schema"),
        required=False,
        help_text=_("Enter a valid JSON schema to define supported allocation attributes."),
    )


class NestedGroupModelBulkEditForm(TenancyBulkEditForm, ColdFrontModelBulkEditForm):
    """
    Bulk edit form for models which inherit from NestedGroupModel.
    """

    description = forms.CharField(
        label=_("Description"),
        max_length=200,
        required=False,
    )
    comments = CommentField()
