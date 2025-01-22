from django.core.management.base import BaseCommand

from coldfront.plugins.announcements.models import AnnouncementStatusChoice, AnnouncementCategoryChoice


class Command(BaseCommand):
    help = 'Add default announcement related choices'

    def handle(self, *args, **options):

        for status_choice in ['Active', 'Removed']:
            AnnouncementStatusChoice.objects.get_or_create(name=status_choice)

        for category_choice in ['Compute', 'Storage', 'Service']:
            AnnouncementCategoryChoice.objects.get_or_create(name=category_choice)
