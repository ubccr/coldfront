from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, User

from coldfront.core.user.admin import EmailAddressInline


class UserInLine(admin.TabularInline):
    model = User.groups.through
    readonly_fields = ('user',)
    extra = 0
    can_delete = False


class GroupsAdmin(GroupAdmin):
    list_display = ["name", "pk"]
    inlines = [UserInLine]


class UsersAdmin(UserAdmin):
    list_display = ["username", "email", "first_name", "last_name", "is_staff"]
    inlines = [EmailAddressInline]


admin.site.unregister(Group)
admin.site.register(Group, GroupsAdmin)

admin.site.unregister(User)
admin.site.register(User, UsersAdmin)