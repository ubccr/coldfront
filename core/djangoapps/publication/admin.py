from django.contrib import admin

from core.djangoapps.publication.models import (PublicationSource, Publication)


@admin.register(PublicationSource)
class PublicationSourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'url',)


@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'year')
    search_fields = ('project__pi__username', 'project__pi__last_name', )
