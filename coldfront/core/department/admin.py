
from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from coldfront.core.department.models import Department, DepartmentMember, DepartmentProject


MEMBER_FIELD = 'user'
DEPARTMENT_FIELD = 'organization'
STATUS_FIELD = 'active'

@admin.register(Department)
class DepartmentAdmin(SimpleHistoryAdmin):
    readonly_fields_change = ('created', 'modified')
    fields_change = ('name', 'rank', 'biller')
    list_display = ('pk', 'name', 'rank', 'biller' )
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
    fields_change = ( MEMBER_FIELD, DEPARTMENT_FIELD, 'role', STATUS_FIELD)
    list_display = ('pk',  MEMBER_FIELD,  DEPARTMENT_FIELD,  STATUS_FIELD)
    list_filter = ( DEPARTMENT_FIELD, STATUS_FIELD)
    search_fields = ( MEMBER_FIELD, DEPARTMENT_FIELD)
    raw_id_fields = ( DEPARTMENT_FIELD, MEMBER_FIELD, )

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
    list_display = ( DEPARTMENT_FIELD, 'project')
    list_filter = ( DEPARTMENT_FIELD, )
