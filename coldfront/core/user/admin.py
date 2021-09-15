from django.contrib import admin
from django.core.exceptions import ValidationError

from coldfront.core.user.models import UserProfile, EmailAddress


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
    search_fields = ('user', 'email', )
    fields = ('email', 'user', 'is_primary', 'is_verified', )
    actions = ('make_primary', )
    readonly_fields = ('is_primary', )

    def delete_model(self, request, obj):
        if obj.is_primary:
            raise ValidationError('Cannot delete primary email. Unset primary status in list display before deleting.')
        else:
            super().delete_model(request, obj)

    @admin.action(description='Make selected primary email')
    def make_primary(self, request, queryset):
        # (a) unset the current primary, (b) set the selected one as primary, and (c) update user.email
        for emailaddress in queryset:
            for primary_email in EmailAddress.objects.filter(user=emailaddress.user).filter(is_primary=True):
                primary_email.is_primary = False
                primary_email.save()

            emailaddress.is_primary = True
            emailaddress.save()

    def delete_queryset(self, request, queryset):
        queryset.filter(is_primary=False).delete()

