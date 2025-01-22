from django import template
from coldfront.plugins.announcements.models import Announcement

register = template.Library()


@register.filter
def get_unread_count(user):
    total_announcements = Announcement.objects.filter(status__name='Active').count()
    read_announcements = Announcement.objects.filter(status__name='Active', viewed_by=user).count()
    return total_announcements - read_announcements