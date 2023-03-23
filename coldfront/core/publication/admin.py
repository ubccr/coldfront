from django.contrib import admin
from coldfront.core.utils.common import import_from_settings
from simple_history.admin import SimpleHistoryAdmin

from coldfront.core.publication.models import Publication, PublicationSource
PUBLICATION_ENABLE = import_from_settings('PUBLICATION_ENABLE', False)

if PUBLICATION_ENABLE:
    @admin.register(PublicationSource)
    class PublicationSourceAdmin(SimpleHistoryAdmin):
        list_display = ('name', 'url',)


    @admin.register(Publication)
    class PublicationAdmin(SimpleHistoryAdmin):
        list_display = ('title', 'author', 'journal', 'year')
        search_fields = ('project__pi__username', 'project__pi__last_name', 'title')
