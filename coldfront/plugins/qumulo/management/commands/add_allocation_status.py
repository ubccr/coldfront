from coldfront.core.allocation.models import AllocationStatusChoice
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        print("Adding Allocation Statuses")
        AllocationStatusChoice.objects.get_or_create(name="Pending")
        AllocationStatusChoice.objects.get_or_create(name="Invalid")
        AllocationStatusChoice.objects.get_or_create(name="Ready for deletion")
        AllocationStatusChoice.objects.get_or_create(name="Deleted")
