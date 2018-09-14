from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from core.djangoapps.publication.models import Publication, PublicationSource


@admin.register(PublicationSource)
class PublicationSourceAdmin(SimpleHistoryAdmin):
    list_display = ('name', 'url',)


@admin.register(Publication)
class PublicationAdmin(SimpleHistoryAdmin):
    list_display = ('title', 'author', 'year')
    search_fields = ('project__pi__username', 'project__pi__last_name', 'title')
