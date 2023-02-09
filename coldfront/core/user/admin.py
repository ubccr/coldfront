from django.contrib import admin

from allauth.account.models import EmailAddress

from coldfront.core.user.models import UserProfile


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


class EmailAddressInline(admin.TabularInline):
    model = EmailAddress
    extra = 0
