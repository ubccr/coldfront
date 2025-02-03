from django.contrib import admin

from coldfront.core.school.models import School


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = (
        'description',
    )
    search_fields = ['description']
