from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from coldfront.plugins.announcements.models import (Announcement, 
                                                    AnnouncementCategoryChoice, 
                                                    AnnouncementMailingListChoice, 
                                                    AnnouncementStatusChoice)


@admin.register(Announcement)
class AnnouncementAdmin(SimpleHistoryAdmin):
    list_display = ('title', 'category_list', 'status', 'pinned', 'created', 'modified', )
    search_fields = ('title', 'categories', )
    list_filter = ('categories', 'status', 'pinned', )
    filter_horizontal = ('categories', 'viewed_by', 'mailing_lists')

    def category_list(self, obj):
        return ', '.join([category.name for category in obj.categories.all()])


@admin.register(AnnouncementCategoryChoice)
class AnnouncementCategoryChoiceAdmin(admin.ModelAdmin):
    list_display = ('name', )
    search_fields = ('name', )


@admin.register(AnnouncementMailingListChoice)
class AnnouncementMailingListChoiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'value', )


@admin.register(AnnouncementStatusChoice)
class AnnouncementStatusChoiceAdmin(admin.ModelAdmin):
    list_display = ('name', )
