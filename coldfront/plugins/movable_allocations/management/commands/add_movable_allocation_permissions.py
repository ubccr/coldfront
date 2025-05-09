from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from coldfront.core.allocation.models import Allocation


class Command(BaseCommand):
    help = 'Add permissions for movable allocations'

    def handle(self, *args, **options):
        content_type = ContentType.objects.get_for_model(Allocation)
        Permission.objects.get_or_create(
            content_type=content_type,
            codename='can_move_allocations',
            name='Can move allocations'
        )
