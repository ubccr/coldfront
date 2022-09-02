
from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from coldfront.core.department.models import (
                                            Department,
                                            DepartmentMember,
                                            DepartmentProject,
                                                )


# class DepartmentProjectInline(admin.TabularInline):
#     model = DepartmentProject
#     extra = 0
#     fields = ('project',)
member_field = 'user'
department_field = 'organization'
status_field = 'active'

@admin.register(Department)
class DepartmentAdmin(SimpleHistoryAdmin):
    readonly_fields_change = ('created', 'modified')
    fields_change = ('name', 'rank', 'biller')#, 'projects')
    list_display = ('pk', 'name', 'rank', 'biller' )
    # inlines = [#DepartmentMemberInline,
    #            DepartmentProjectInline]
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



@admin.register(DepartmentMember)
class DepartmentMemberAdmin(SimpleHistoryAdmin):
    readonly_fields_change = ('created', 'modified')
    fields_change = (member_field, department_field, 'role', status_field)
    list_display = ('pk', member_field, department_field, status_field)
    list_filter = (department_field, status_field)
    search_fields = (
        member_field,
        department_field
    )
    raw_id_fields = (department_field, member_field, )

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
    # fields_change = (department_field, 'project')
    list_display = (department_field, 'project')
    list_filter = (department_field, )
