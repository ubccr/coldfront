from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin
from django.contrib.auth.models import Group, User


class UserInLine(admin.TabularInline):
    model = User.groups.through
    readonly_fields = ('user',)
    extra = 0
    can_delete = False


class GroupsAdmin(GroupAdmin):
    list_display = ["name", "pk"]
    inlines = [UserInLine]


admin.site.unregister(Group)
admin.site.register(Group, GroupsAdmin)
