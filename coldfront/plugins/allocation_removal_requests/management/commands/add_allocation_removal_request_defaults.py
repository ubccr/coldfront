from django.core.management.base import BaseCommand

from coldfront.core.allocation.models import AllocationStatusChoice
from coldfront.plugins.allocation_removal_requests.models import AllocationRemovalStatusChoice


class Command(BaseCommand):
    help = 'Add default allocation removal related choices'

    def handle(self, *args, **options):
        for choice in ('Approved', 'Pending', 'Denied', ):
            AllocationRemovalStatusChoice.objects.get_or_create(name=choice)

        for choice in ('Removal Requested', 'Removed'):
            AllocationStatusChoice.objects.get_or_create(name=choice)
