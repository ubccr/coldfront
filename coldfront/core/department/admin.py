from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from ifxuser.models import UserAffiliation
from coldfront.core.department.models import Department, DepartmentMember


class DepartmentParentsInline(admin.TabularInline):
    """Department parents inline"""
    model = Department.parents.through
    extra = 1
    fk_name = 'child'
    autocomplete_fields = ('parent',)


class DepartmentChildrenInline(admin.TabularInline):
    """Department children inline"""
    model = Department.children.through
    extra = 1
    fk_name = 'parent'
    autocomplete_fields = ('child',)


class UserAffiliationInlineAdmin(admin.TabularInline):
    """Inline of affiliations to be used with the Person form"""
    model = UserAffiliation
    autocomplete_fields = ('user', 'organization')
    extra = 1


class DepartmentContactsInline(admin.TabularInline):
    """Inline for contacts in the department admin"""
    model = Department.contacts.through
    extra = 1
    autocomplete_fields = ('contact', 'organization')



class DepartmentParentsInline(admin.TabularInline):
    """Department parents inline"""
    model = Department.parents.through
    extra = 1
    fk_name = 'child'
    autocomplete_fields = ('parent',)


class DepartmentChildrenInline(admin.TabularInline):
    """Department children inline"""
    model = Department.children.through
    extra = 1
    fk_name = 'parent'
    autocomplete_fields = ('child',)

class UserAffiliationInlineAdmin(admin.TabularInline):
    """Inline of affiliations to be used with the Person form"""
    model = UserAffiliation
    autocomplete_fields = ('user', 'organization')
    extra = 1


class DepartmentContactsInline(admin.TabularInline):
    """Inline for contacts in the department admin"""
    model = Department.contacts.through
    extra = 1
    autocomplete_fields = ('contact', 'organization')


@admin.register(Department)
class DepartmentAdmin(SimpleHistoryAdmin):
    readonly_fields_change = ('created', 'modified')
    fields_change = ('name', 'rank')
    list_display = ('pk', 'name', 'rank', 'org_tree')
    search_fields = ('name', 'rank', 'slug', 'org_tree')
    list_filter = ('org_tree', 'rank')
    inlines = [
        DepartmentParentsInline,
        DepartmentChildrenInline,
        DepartmentContactsInline,
        UserAffiliationInlineAdmin,
    ]

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
    fields_change = ('user', 'organization', 'role', 'active')
    list_display = ('pk', 'user', 'organization', 'active')
    list_filter = ('role', 'active', 'organization__org_tree')
    search_fields = ('organization__name', 'user__full_name', 'user__username')
    raw_id_fields = ('organization', 'user')


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