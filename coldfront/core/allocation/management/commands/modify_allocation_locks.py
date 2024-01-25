from django.core.management.base import BaseCommand, CommandError

from coldfront.core.allocation.models import Allocation

class Command(BaseCommand):
    help = 'Lock/unlock all allocations containing a specific resource'

    def add_arguments(self, parser):
        parser.add_argument("--resource", type=str)
        parser.add_argument("--lock", type=int)

    def handle(self, *args, **kwargs):
        resource = kwargs.get("resource")
        if not resource:
            raise CommandError("Please provide a resource")
        
        lock = kwargs.get("lock")
        if lock not in [0, 1]:
            raise CommandError("Please specify 0 (unlock) or 1 (lock)")
        lock = bool(lock)
        
        allocation_objs = Allocation.objects.filter(resources__name=resource)
        for allocation_obj in allocation_objs:
            allocation_obj.is_locked = lock
            allocation_obj.save()

            print (allocation_obj.is_locked)

