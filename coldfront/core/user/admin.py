from django.contrib import admin
from django.contrib import messages
from django.core.exceptions import ValidationError

from coldfront.core.user.models import UserProfile, EmailAddress
from coldfront.core.user.utils import update_user_primary_email_address

import logging


logger = logging.getLogger(__name__)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('username', 'first_name', 'last_name', 'is_pi')
    ordering = ('user__username', 'user__last_name')
    list_filter = ('is_pi',)
    search_fields = ['user__username', 'user__first_name', 'user__last_name']

    def username(self, obj):
        return obj.user.username

    def first_name(self, obj):
        return obj.user.first_name

    def last_name(self, obj):
        return obj.user.last_name


@admin.register(EmailAddress)
class EmailAddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'email', 'is_primary', 'is_verified', )
    ordering = ('user', '-is_primary', '-is_verified', 'email', )
    list_filter = ('is_primary', 'is_verified', )
    search_fields = [
        'user__username', 'user__first_name', 'user__last_name', 'email']
    fields = ('email', 'user', 'is_primary', 'is_verified', )
    actions = ('make_primary', )
    readonly_fields = ('is_primary', 'is_verified', )

    def delete_model(self, request, obj):
        if obj.is_primary:
            raise ValidationError(
                'Cannot delete primary email. Unset primary status in list '
                'display before deleting.')
        else:
            super().delete_model(request, obj)

    @admin.action(description='Make selected primary')
    def make_primary(self, request, queryset):
        """Set the EmailAddresses in the given queryset as the primary
        addresses of their respective users.

        Currently, admins are limited to setting at most one address at
        a time."""
        if queryset.count() > 1:
            raise ValidationError(
                'Cannot set more than one primary email address at a time.')
        for email_address in queryset:
            user = email_address.user
            try:
                update_user_primary_email_address(email_address)
            except ValueError:
                raise ValidationError(
                    'Cannot set an unverified email address as primary.')
            except Exception as e:
                message = (
                    f'Encountered unexpected exception when updating User '
                    f'{user.pk}\'s primary EmailAddress to '
                    f'{email_address.pk}. Details:')
                logger.error(message)
                logger.exception(e)
                raise ValidationError(
                    f'Failed to set {email_address.pk} as primary. See the '
                    f'log for details.')
            else:
                message = (
                    f'Set User {user.pk}\'s primary EmailAddress to '
                    f'{email_address.email}.')
                messages.success(request, message)

    def delete_queryset(self, request, queryset):
        """Delete EmailAddresses in the given queryset, skipping those
        that are primary."""
        num_primary, num_non_primary = 0, 0
        for email_address in queryset:
            if email_address.is_primary:
                num_primary = num_primary + 1
            else:
                email_address.delete()
                num_non_primary = num_non_primary + 1

        success_message = (
            f'Deleted {num_non_primary} non-primary EmailAddresses.')
        messages.success(request, success_message)

        if num_primary > 0:
            error_message = (
                f'Skipped deleting {num_primary} primary EmailAddresses.')
            messages.error(request, error_message)


class EmailAddressInline(admin.TabularInline):
    model = EmailAddress
    extra = 0
