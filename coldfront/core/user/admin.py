from django.contrib import admin

from coldfront.core.user.models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('username', 'first_name', 'last_name', 'title', 'is_pi')
    list_filter = ('is_pi', 'title')
    search_fields = ['user__username', 'user__first_name', 'user__last_name']
    readonly_fields = ['title', 'department', 'division']

    def username(self, obj):
        return obj.user.username

    def first_name(self, obj):
        return obj.user.first_name

    def last_name(self, obj):
        return obj.user.last_name
