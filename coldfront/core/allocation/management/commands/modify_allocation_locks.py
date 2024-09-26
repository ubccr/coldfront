import logging

from django.core.management.base import BaseCommand, CommandError

from coldfront.core.allocation.models import Allocation

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Lock/unlock all allocations containing a specific resource'

    def add_arguments(self, parser):
        parser.add_argument('--resource', type=str, required=True)
        parser.add_argument('--lock', type=int, required=True)

    def handle(self, *args, **kwargs):
        resource = kwargs.get('resource')
        lock = kwargs.get('lock')
        if lock not in [0, 1]:
            raise CommandError('Please specify 0 (unlock) or 1 (lock)')
        lock = bool(lock)
        
        allocation_objs = Allocation.objects.filter(resources__name=resource)
        for allocation_obj in allocation_objs:
            allocation_obj.is_locked = lock
            allocation_obj.save()

        logger.info(f'All {resource} allocations were {"locked" if lock else "unlocked"}')
