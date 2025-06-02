# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from coldfront.core.resource.models import (
    AttributeType,
    Resource,
    ResourceAttribute,
    ResourceAttributeType,
    ResourceType,
)


@admin.register(AttributeType)
class AttributeTypeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "created",
        "modified",
    )
    search_fields = ("name",)


@admin.register(ResourceType)
class ResourceTypeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "description",
        "created",
        "modified",
    )
    search_fields = (
        "name",
        "description",
    )


@admin.register(ResourceAttributeType)
class ResourceAttributeTypeAdmin(SimpleHistoryAdmin):
    list_display = (
        "pk",
        "name",
        "attribute_type_name",
        "is_required",
        "is_unique_per_resource",
        "is_value_unique",
        "created",
        "modified",
    )
    search_fields = (
        "name",
        "attribute_type__name",
        "resource_type__name",
    )
    list_filter = ("attribute_type__name", "name", "is_required", "is_unique_per_resource", "is_value_unique")

    def attribute_type_name(self, obj):
        return obj.attribute_type.name


class ResourceAttributeInline(admin.TabularInline):
    model = ResourceAttribute
    fields_change = (
        "resource_attribute_type",
        "value",
    )
    extra = 0

    def get_fields(self, request, obj):
        if obj is None:
            return super().get_fields(request)
        else:
            return self.fields_change


@admin.register(Resource)
class ResourceAdmin(SimpleHistoryAdmin):
    # readonly_fields_change = ('resource_type', )
    fields_change = (
        "resource_type",
        "parent_resource",
        "is_allocatable",
        "name",
        "description",
        "is_available",
        "is_public",
        "requires_payment",
        "allowed_groups",
        "allowed_users",
        "linked_resources",
    )
    list_display = (
        "pk",
        "name",
        "description",
        "parent_resource",
        "is_allocatable",
        "resource_type_name",
        "is_available",
        "is_public",
        "created",
        "modified",
    )
    search_fields = ("name", "description", "resource_type__name")
    list_filter = ("resource_type__name", "is_allocatable", "is_available", "is_public", "requires_payment")
    inlines = [
        ResourceAttributeInline,
    ]
    filter_horizontal = [
        "allowed_groups",
        "allowed_users",
        "linked_resources",
    ]
    save_as = True

    def resource_type_name(self, obj):
        return obj.resource_type.name

    def get_fields(self, request, obj):
        if obj is None:
            return super().get_fields(request)
        else:
            return self.fields_change


@admin.register(ResourceAttribute)
class ResourceAttributeAdmin(SimpleHistoryAdmin):
    list_display = (
        "pk",
        "resource_name",
        "value",
        "resource_attribute_type_name",
        "created",
        "modified",
    )
    search_fields = ("resource__name", "resource_attribute_type__name", "value")
    list_filter = ("resource_attribute_type__name",)

    def resource_name(self, obj):
        return obj.resource.name

    def resource_attribute_type_name(self, obj):
        return obj.resource_attribute_type.name
