from django.core.management.base import BaseCommand

from coldfront.core.allocation.models import Allocation


class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        allocation_objs = Allocation.objects.filter(resources__name='Slate Project')
        for allocation in allocation_objs:
            allocation.is_changeable = True
            allocation.save()