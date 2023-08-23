from django.contrib import admin
from django.contrib import messages
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from coldfront.core.account.utils.queries import update_user_primary_email_address
from django.db import transaction

from coldfront.core.user.admin import EmailAddressInline

import logging


logger = logging.getLogger(__name__)


class UserInLine(admin.TabularInline):
    model = User.groups.through
    readonly_fields = ('user',)
    extra = 0
    can_delete = False


class GroupAdmin(BaseGroupAdmin):
    list_display = ["name", "pk"]
    inlines = [UserInLine]


class UserAdmin(BaseUserAdmin):
    list_display = ["username", "email", "first_name", "last_name", "is_active"]
    inlines = [EmailAddressInline]
    actions = ('activate', )

    @admin.action(description='Activate selected users')
    def activate(self, request, queryset):
        user_pks = set()
        for user in queryset:
            if not user.is_active:
                user.is_active = True
                user.save()
                user_pks.add(user.pk)
        n = len(user_pks)
        messages.success(request, f'Activated {n} users.')
        if n > 0:
            user_pk_str = ", ".join([str(pk) for pk in sorted(user_pks)])
            logger.info(
                f'User {request.user.username} activated the following users: '
                f'{user_pk_str}.')

    @transaction.atomic
    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        if isinstance(formset, EmailAddressInline.formset):
            for instance in instances:
                if instance.primary:
                    update_user_primary_email_address(instance)
        super().save_formset(request, form, formset, change)


admin.site.unregister(Group)
admin.site.register(Group, GroupAdmin)

admin.site.unregister(User)
admin.site.register(User, UserAdmin)
