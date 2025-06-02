# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import textwrap

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from simple_history.admin import SimpleHistoryAdmin

from coldfront.core.allocation.models import (
    Allocation,
    AllocationAccount,
    AllocationAdminNote,
    AllocationAttribute,
    AllocationAttributeChangeRequest,
    AllocationAttributeType,
    AllocationAttributeUsage,
    AllocationChangeRequest,
    AllocationChangeStatusChoice,
    AllocationStatusChoice,
    AllocationUser,
    AllocationUserNote,
    AllocationUserStatusChoice,
    AttributeType,
)


@admin.register(AllocationStatusChoice)
class AllocationStatusChoiceAdmin(admin.ModelAdmin):
    list_display = ("name",)


class AllocationUserInline(admin.TabularInline):
    model = AllocationUser
    extra = 0
    fields = (
        "user",
        "status",
    )
    raw_id_fields = ("user",)


class AllocationAttributeInline(admin.TabularInline):
    model = AllocationAttribute
    extra = 0
    fields = (
        "allocation_attribute_type",
        "value",
    )


class AllocationAdminNoteInline(admin.TabularInline):
    model = AllocationAdminNote
    extra = 0
    fields = (("note", "author", "created"),)
    readonly_fields = ("author", "created")


class AllocationUserNoteInline(admin.TabularInline):
    model = AllocationUserNote
    extra = 0
    fields = (("note", "author", "created"),)
    readonly_fields = ("author", "created")


@admin.register(Allocation)
class AllocationAdmin(SimpleHistoryAdmin):
    readonly_fields_change = (
        "project",
        "justification",
        "created",
        "modified",
    )
    fields_change = (
        "project",
        "resources",
        "quantity",
        "justification",
        "status",
        "start_date",
        "end_date",
        "description",
        "created",
        "modified",
        "is_locked",
        "is_changeable",
    )
    list_display = (
        "pk",
        "project_title",
        "project_pi",
        "resource",
        "quantity",
        "justification",
        "start_date",
        "end_date",
        "status",
        "created",
        "modified",
    )
    inlines = [AllocationUserInline, AllocationAttributeInline, AllocationAdminNoteInline, AllocationUserNoteInline]
    list_filter = ("resources__resource_type__name", "status", "resources__name", "is_locked")
    search_fields = [
        "project__pi__username",
        "project__pi__first_name",
        "project__pi__last_name",
        "resources__name",
        "allocationuser__user__first_name",
        "allocationuser__user__last_name",
        "allocationuser__user__username",
    ]
    filter_horizontal = [
        "resources",
    ]
    raw_id_fields = ("project",)

    def resource(self, obj):
        return obj.get_parent_resource

    def project_pi(self, obj):
        return obj.project.pi.username

    def project_title(self, obj):
        return textwrap.shorten(obj.project.title, width=50)

    def get_fields(self, request, obj):
        if obj is None:
            return super().get_fields(request)
        else:
            return self.fields_change

    def get_readonly_fields(self, request, obj):
        if obj is None:
            # We are adding an object
            return super().get_readonly_fields(request)
        else:
            return self.readonly_fields_change

    def get_inline_instances(self, request, obj=None):
        if obj is None:
            # We are adding an object
            return []
        else:
            return super().get_inline_instances(request)

    def save_formset(self, request, form, formset, change):
        if formset.model in [AllocationAdminNote, AllocationUserNote]:
            instances = formset.save(commit=False)
            for instance in instances:
                instance.author = request.user
                instance.save()
        else:
            formset.save()


@admin.register(AttributeType)
class AttributeTypeAdmin(admin.ModelAdmin):
    list_display = ("name",)


@admin.register(AllocationAttributeType)
class AllocationAttributeTypeAdmin(admin.ModelAdmin):
    list_display = ("pk", "name", "attribute_type", "has_usage", "is_private")


class AllocationAttributeUsageInline(admin.TabularInline):
    model = AllocationAttributeUsage
    extra = 0


class UsageValueFilter(admin.SimpleListFilter):
    title = _("value")

    parameter_name = "value"

    def lookups(self, request, model_admin):
        return (
            (">=0", _("Greater than or equal to 0")),
            (">10", _("Greater than 10")),
            (">100", _("Greater than 100")),
            (">1000", _("Greater than 1000")),
            (">10000", _("Greater than 10000")),
        )

    def queryset(self, request, queryset):
        if self.value() == ">=0":
            return queryset.filter(allocationattributeusage__value__gte=0)

        if self.value() == ">10":
            return queryset.filter(allocationattributeusage__value__gte=10)

        if self.value() == ">100":
            return queryset.filter(allocationattributeusage__value__gte=100)

        if self.value() == ">1000":
            return queryset.filter(allocationattributeusage__value__gte=1000)


@admin.register(AllocationAttribute)
class AllocationAttributeAdmin(SimpleHistoryAdmin):
    readonly_fields_change = ("allocation", "allocation_attribute_type", "created", "modified", "project_title")
    fields_change = (
        "project_title",
        "allocation",
        "allocation_attribute_type",
        "value",
        "created",
        "modified",
    )
    list_display = (
        "pk",
        "project",
        "pi",
        "resource",
        "allocation_status",
        "allocation_attribute_type",
        "value",
        "usage",
        "created",
        "modified",
    )
    inlines = [
        AllocationAttributeUsageInline,
    ]
    list_filter = (UsageValueFilter, "allocation_attribute_type", "allocation__status", "allocation__resources")
    search_fields = (
        "allocation__project__pi__first_name",
        "allocation__project__pi__last_name",
        "allocation__project__pi__username",
        "allocation__allocationuser__user__first_name",
        "allocation__allocationuser__user__last_name",
        "allocation__allocationuser__user__username",
    )

    def usage(self, obj):
        if hasattr(obj, "allocationattributeusage"):
            return obj.allocationattributeusage.value
        else:
            return "N/A"

    def resource(self, obj):
        return obj.allocation.get_parent_resource

    def allocation_status(self, obj):
        return obj.allocation.status

    def pi(self, obj):
        return "{} {} ({})".format(
            obj.allocation.project.pi.first_name,
            obj.allocation.project.pi.last_name,
            obj.allocation.project.pi.username,
        )

    def project(self, obj):
        return textwrap.shorten(obj.allocation.project.title, width=50)

    def project_title(self, obj):
        return obj.allocation.project.title

    def get_fields(self, request, obj):
        if obj is None:
            return super().get_fields(request)
        else:
            return self.fields_change

    def get_readonly_fields(self, request, obj):
        if obj is None:
            # We are adding an object
            return super().get_readonly_fields(request)
        else:
            return self.readonly_fields_change

    def get_inline_instances(self, request, obj=None):
        if obj is None:
            # We are adding an object
            return []
        else:
            return super().get_inline_instances(request)


@admin.register(AllocationUserStatusChoice)
class AllocationUserStatusChoiceAdmin(admin.ModelAdmin):
    list_display = ("name",)


@admin.register(AllocationUser)
class AllocationUserAdmin(SimpleHistoryAdmin):
    readonly_fields_change = (
        "allocation",
        "user",
        "resource",
        "created",
        "modified",
    )
    fields_change = (
        "allocation",
        "user",
        "status",
        "created",
        "modified",
    )
    list_display = (
        "pk",
        "project",
        "project_pi",
        "resource",
        "allocation_status",
        "user_info",
        "status",
        "created",
        "modified",
    )
    list_filter = (
        "status",
        "allocation__status",
        "allocation__resources",
    )
    search_fields = (
        "user__first_name",
        "user__last_name",
        "user__username",
    )
    raw_id_fields = (
        "allocation",
        "user",
    )

    def allocation_status(self, obj):
        return obj.allocation.status

    def user_info(self, obj):
        return "{} {} ({})".format(obj.user.first_name, obj.user.last_name, obj.user.username)

    def resource(self, obj):
        return obj.allocation.resources.first()

    def project_pi(self, obj):
        return obj.allocation.project.pi

    def project(self, obj):
        return textwrap.shorten(obj.allocation.project.title, width=50)

    def get_fields(self, request, obj):
        if obj is None:
            return super().get_fields(request)
        else:
            return self.fields_change

    def get_readonly_fields(self, request, obj):
        if obj is None:
            # We are adding an object
            return super().get_readonly_fields(request)
        else:
            return self.readonly_fields_change

    def get_inline_instances(self, request, obj=None):
        if obj is None:
            # We are adding an object
            return []
        else:
            return super().get_inline_instances(request)

    def set_active(self, request, queryset):
        queryset.update(status=AllocationUserStatusChoice.objects.get(name="Active"))

    def set_denied(self, request, queryset):
        queryset.update(status=AllocationUserStatusChoice.objects.get(name="Denied"))

    def set_removed(self, request, queryset):
        queryset.update(status=AllocationUserStatusChoice.objects.get(name="Removed"))

    set_active.short_description = "Set Selected User's Status To Active"

    set_denied.short_description = "Set Selected User's Status To Denied"

    set_removed.short_description = "Set Selected User's Status To Removed"

    actions = [
        set_active,
        set_denied,
        set_removed,
    ]


class ValueFilter(admin.SimpleListFilter):
    title = _("value")

    parameter_name = "value"

    def lookups(self, request, model_admin):
        return (
            (">0", _("Greater than > 0")),
            (">10", _("Greater than > 10")),
            (">100", _("Greater than > 100")),
            (">1000", _("Greater than > 1000")),
        )

    def queryset(self, request, queryset):
        if self.value() == ">0":
            return queryset.filter(value__gt=0)

        if self.value() == ">10":
            return queryset.filter(value__gt=10)

        if self.value() == ">100":
            return queryset.filter(value__gt=100)

        if self.value() == ">1000":
            return queryset.filter(value__gt=1000)


@admin.register(AllocationAttributeUsage)
class AllocationAttributeUsageAdmin(SimpleHistoryAdmin):
    list_display = (
        "allocation_attribute",
        "project",
        "project_pi",
        "resource",
        "value",
    )
    readonly_fields = ("allocation_attribute",)
    fields = (
        "allocation_attribute",
        "value",
    )
    list_filter = (
        "allocation_attribute__allocation_attribute_type",
        "allocation_attribute__allocation__resources",
        ValueFilter,
    )

    def resource(self, obj):
        return obj.allocation_attribute.allocation.resources.first().name

    def project(self, obj):
        return obj.allocation_attribute.allocation.project.title

    def project_pi(self, obj):
        return obj.allocation_attribute.allocation.project.pi.username


@admin.register(AllocationAccount)
class AllocationAccountAdmin(SimpleHistoryAdmin):
    list_display = (
        "name",
        "user",
    )


@admin.register(AllocationChangeStatusChoice)
class AllocationChangeStatusChoiceAdmin(admin.ModelAdmin):
    list_display = ("name",)


@admin.register(AllocationChangeRequest)
class AllocationChangeRequestAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "allocation",
        "status",
        "end_date_extension",
        "justification",
        "notes",
    )


@admin.register(AllocationAttributeChangeRequest)
class AllocationAttributeChangeRequestAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "allocation_change_request",
        "allocation_attribute",
        "new_value",
    )
