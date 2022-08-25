
from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from coldfront.core.department.models import (
                                            Department,
                                            DepartmentRank,
                                            DepartmentMember,
                                            DepartmentMemberRole,
                                            DepartmentMemberStatus,
                                            DepartmentProject,
                                                )


class DepartmentProjectInline(admin.TabularInline):
    model = DepartmentProject
    extra = 0
    fields = ('project',)


@admin.register(Department)
class DepartmentAdmin(SimpleHistoryAdmin):
    readonly_fields_change = ('created', 'modified')
    fields_change = ('name', 'rank', 'biller', 'created', 'modified')#, 'projects')
    list_display = ('pk', 'name', 'rank', 'biller', 'created', 'modified' )
    inlines = [#DepartmentMemberInline,
               DepartmentProjectInline]
    search_fields = ('name', 'rank', 'biller')


    def get_fields(self, request, obj):
        if obj is None:
            return super().get_fields(request)
        return self.fields_change

    def get_readonly_fields(self, request, obj):
        if obj is None:
            return super().get_readonly_fields(request)
        return self.readonly_fields_change

    def get_inline_instances(self, request, obj=None):
        if obj is None:
            return []
        return super().get_inline_instances(request)


@admin.register(DepartmentRank)
class DepartmentRankAdmin(admin.ModelAdmin):
    list_display = ('pk', 'name')


@admin.register(DepartmentMemberRole)
class DepartmentMemberRoleAdmin(admin.ModelAdmin):
    list_display = ('pk', 'name')


@admin.register(DepartmentMemberStatus)
class DepartmentMemberStatusAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(DepartmentMember)
class DepartmentMemberAdmin(SimpleHistoryAdmin):
    readonly_fields_change = ('created', 'modified')
    fields_change = ('member', 'department', 'role', 'status', 'enable_notifications',
                                                        'created', 'modified')
    list_display = ('pk', 'member', 'department', 'status', 'enable_notifications',
                    'created', 'modified')
    list_filter = ('department__name', 'status', 'enable_notifications')
    search_fields = (
        'member__first_name',
        'member__last_name',
        'member__username',
        'department__name'
    )
    raw_id_fields = ('department', 'member', )

    def get_fields(self, request, obj):
        if obj is None:
            return super().get_fields(request)
        return self.fields_change

    def get_readonly_fields(self, request, obj):
        if obj is None:
            # We are adding an object
            return super().get_readonly_fields(request)
        return self.readonly_fields_change

    def get_inline_instances(self, request, obj=None):
        if obj is None:
            return []
        return super().get_inline_instances(request)


@admin.register(DepartmentProject)
class DepartmentProjectAdmin(SimpleHistoryAdmin):
    readonly_fields_change = ('created', 'modified')
    # fields_change = ('department', 'project')
    list_display = ('department', 'project', 'created', 'modified')
    list_filter = ('department', )
