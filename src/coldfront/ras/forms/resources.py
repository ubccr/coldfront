# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django import forms
from django.utils.translation import gettext_lazy as _

from coldfront.forms import (
    NestedGroupModelForm,
    NestedGroupModelImportForm,
    OrganizationalModelForm,
    PrimaryModelImportForm,
    TenancyForm,
    TenancyImportForm,
)
from coldfront.forms.fields import CSVModelChoiceField, DynamicModelChoiceField, JSONField, SlugField
from coldfront.forms.layout import FieldSet
from coldfront.ras.models import Resource, ResourceType


class ResourceTypeForm(OrganizationalModelForm):
    slug = SlugField()

    class Meta:
        model = ResourceType
        fields = [
            "name",
            "slug",
            "color",
            "description",
            "tags",
        ]

    fieldsets = (
        FieldSet(
            "name",
            "slug",
            "color",
            "description",
            name=_("Resource Type"),
        ),
        FieldSet(
            "tags",
            name=_("Tags"),
        ),
    )


class ResourceForm(TenancyForm, NestedGroupModelForm):
    resource_type = forms.ModelChoiceField(
        queryset=ResourceType.objects.all(),
        label=_("Resource Type"),
        required=False,
    )

    schema = JSONField(
        label=_("Schema"),
        required=False,
        help_text=_("Enter a valid JSON schema to define supported allocation attributes."),
    )

    parent = DynamicModelChoiceField(
        label=_("Parent"),
        queryset=Resource.objects.all(),
        required=False,
    )

    class Meta:
        model = Resource
        fields = [
            "name",
            "slug",
            "parent",
            "resource_type",
            "status",
            "schema",
            "description",
            "locked",
            "tags",
            "tenant_group",
            "tenant",
        ]

    fieldsets = (
        FieldSet(
            "resource_type",
            name=_("Resource Type"),
        ),
        FieldSet(
            "name",
            "slug",
            "parent",
            "status",
            "description",
            "locked",
            "schema",
            name=_("Resource"),
        ),
        FieldSet(
            "tenant_group",
            "tenant",
            name=_("Tenant"),
        ),
        FieldSet(
            "tags",
            name=_("Tags"),
        ),
    )


class ResourceImportForm(TenancyImportForm, NestedGroupModelImportForm):
    parent = CSVModelChoiceField(
        label=_("Parent"),
        queryset=Resource.objects.all(),
        required=False,
        to_field_name="name",
        help_text=_("Parent resource"),
    )

    resource_type = CSVModelChoiceField(
        label=_("Resource Type"),
        queryset=ResourceType.objects.all(),
        to_field_name="name",
        help_text=_("Resource Type"),
    )

    class Meta:
        model = Resource
        fields = [
            "name",
            "slug",
            "resource_type",
            "parent",
            "status",
            "schema",
            "description",
            "tags",
            "tenant",
        ]


class ResourceTypeImportForm(PrimaryModelImportForm):
    class Meta:
        model = ResourceType
        fields = [
            "name",
            "slug",
            "color",
            "description",
            "tags",
        ]
