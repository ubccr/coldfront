# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import textwrap

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from simple_history.admin import SimpleHistoryAdmin

from coldfront.core.project.models import (
    AttributeType,
    Project,
    ProjectAdminComment,
    ProjectAttribute,
    ProjectAttributeType,
    ProjectAttributeUsage,
    ProjectReview,
    ProjectStatusChoice,
    ProjectUser,
    ProjectUserMessage,
    ProjectUserRoleChoice,
    ProjectUserStatusChoice,
)
from coldfront.core.utils.common import import_from_settings

PROJECT_CODE = import_from_settings("PROJECT_CODE", False)
PROJECT_INSTITUTION_EMAIL_MAP = import_from_settings("PROJECT_INSTITUTION_EMAIL_MAP", False)


@admin.register(ProjectStatusChoice)
class ProjectStatusChoiceAdmin(admin.ModelAdmin):
    list_display = ("name",)


@admin.register(ProjectUserRoleChoice)
class ProjectUserRoleChoiceAdmin(admin.ModelAdmin):
    list_display = ("name",)


@admin.register(ProjectUserStatusChoice)
class ProjectUserStatusChoiceAdmin(admin.ModelAdmin):
    list_display = ("name",)


@admin.register(ProjectUser)
class ProjectUserAdmin(SimpleHistoryAdmin):
    fields_change = (
        "user",
        "project",
        "role",
        "status",
        "created",
        "modified",
    )
    readonly_fields_change = (
        "user",
        "project",
        "created",
        "modified",
    )
    list_display = (
        "pk",
        "project_title",
        "PI",
        "User",
        "role",
        "status",
        "created",
        "modified",
    )
    list_filter = ("role", "status")
    search_fields = ["user__username", "user__first_name", "user__last_name"]
    raw_id_fields = ("user", "project")

    def project_title(self, obj):
        return textwrap.shorten(obj.project.title, width=50)

    def PI(self, obj):
        return "{} {} ({})".format(obj.project.pi.first_name, obj.project.pi.last_name, obj.project.pi.username)

    def User(self, obj):
        return "{} {} ({})".format(obj.user.first_name, obj.user.last_name, obj.user.username)

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
            return super().get_inline_instances(request)
        else:
            return [inline(self.model, self.admin_site) for inline in self.inlines]


class ProjectUserInline(admin.TabularInline):
    model = ProjectUser
    fields = [
        "user",
        "project",
        "role",
        "status",
        "enable_notifications",
    ]
    readonly_fields = [
        "user",
        "project",
    ]
    extra = 0


class ProjectAdminCommentInline(admin.TabularInline):
    model = ProjectAdminComment
    extra = 0
    fields = (("comment", "author", "created"),)
    readonly_fields = ("author", "created")


class ProjectUserMessageInline(admin.TabularInline):
    model = ProjectUserMessage
    extra = 0
    fields = (("message", "author", "created"),)
    readonly_fields = ("author", "created")


class ProjectAttributeInLine(admin.TabularInline):
    model = ProjectAttribute
    extra = 0
    fields = (
        "proj_attr_type",
        "value",
    )


@admin.register(AttributeType)
class AttributeTypeAdmin(admin.ModelAdmin):
    list_display = ("name",)


@admin.register(ProjectAttributeType)
class ProjectAttributeTypeAdmin(admin.ModelAdmin):
    list_display = ("pk", "name", "attribute_type", "has_usage", "is_private")


class ProjectAttributeUsageInline(admin.TabularInline):
    model = ProjectAttributeUsage
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


@admin.register(ProjectAttribute)
class ProjectAttributeAdmin(SimpleHistoryAdmin):
    readonly_fields_change = ("proj_attr_type", "created", "modified", "project_title")
    fields_change = (
        "project_title",
        "proj_attr_type",
        "value",
        "created",
        "modified",
    )
    list_display = (
        "pk",
        "project",
        "pi",
        "project_status",
        "proj_attr_type",
        "value",
        "usage",
        "created",
        "modified",
    )
    inlines = [
        ProjectAttributeUsageInline,
    ]
    list_filter = (UsageValueFilter, "proj_attr_type", "project__status")
    search_fields = (
        "project__pi__first_name",
        "project__pi__last_name",
        "project__pi__username",
        "project__projectuser__user__first_name",
        "project__projectuser__user__last_name",
        "project__projectuser__user__username",
    )

    def usage(self, obj):
        if hasattr(obj, "projectattributeusage"):
            return obj.projectattributeusage.value
        else:
            return "N/A"

    def project_status(self, obj):
        return obj.project.status

    def pi(self, obj):
        return "{} {} ({})".format(obj.project.pi.first_name, obj.project.pi.last_name, obj.project.pi.username)

    def project(self, obj):
        return textwrap.shorten(obj.project.title, width=50)

    def project_title(self, obj):
        return obj.project.title

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


@admin.register(ProjectAttributeUsage)
class ProjectAttributeUsageAdmin(SimpleHistoryAdmin):
    list_display = (
        "project_attribute",
        "project",
        "project_pi",
        "value",
    )
    readonly_fields = ("project_attribute",)
    fields = (
        "project_attribute",
        "value",
    )
    list_filter = (
        "project_attribute__proj_attr_type",
        ValueFilter,
    )

    def project(self, obj):
        return obj.project_attribute.project.title

    def project_pi(self, obj):
        return obj.project_attribute.project.pi.username


@admin.register(Project)
class ProjectAdmin(SimpleHistoryAdmin):
    fields_change = (
        "title",
        "pi",
        "description",
        "status",
        "requires_review",
        "force_review",
        "created",
        "modified",
    )
    readonly_fields_change = (
        "created",
        "modified",
    )
    list_display = ("pk", "title", "PI", "created", "modified", "status")
    search_fields = [
        "pi__username",
        "projectuser__user__username",
        "projectuser__user__last_name",
        "projectuser__user__last_name",
        "title",
    ]
    list_filter = ("status", "force_review")
    inlines = [ProjectUserInline, ProjectAdminCommentInline, ProjectUserMessageInline, ProjectAttributeInLine]
    raw_id_fields = [
        "pi",
    ]

    def PI(self, obj):
        return "{} {} ({})".format(obj.pi.first_name, obj.pi.last_name, obj.pi.username)

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

    def get_list_display(self, request):
        if not (PROJECT_CODE or PROJECT_INSTITUTION_EMAIL_MAP):
            return self.list_display

        list_display = list(self.list_display)

        if PROJECT_CODE:
            list_display.insert(1, "project_code")

        if PROJECT_INSTITUTION_EMAIL_MAP:
            list_display.insert(2, "institution")

        return tuple(list_display)

    def save_formset(self, request, form, formset, change):
        if formset.model in [ProjectAdminComment, ProjectUserMessage]:
            instances = formset.save(commit=False)
            for instance in instances:
                instance.author = request.user
                instance.save()
        else:
            formset.save()


@admin.register(ProjectReview)
class ProjectReviewAdmin(SimpleHistoryAdmin):
    list_display = ("pk", "project", "PI", "reason_for_not_updating_project", "created", "status")
    search_fields = [
        "project__pi__username",
        "project__pi__first_name",
        "project__pi__last_name",
    ]
    list_filter = ("status",)

    def PI(self, obj):
        return "{} {} ({})".format(obj.project.pi.first_name, obj.project.pi.last_name, obj.project.pi.username)
