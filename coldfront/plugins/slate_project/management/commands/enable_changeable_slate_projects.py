from django.core.management.base import BaseCommand

from coldfront.core.allocation.models import Allocation


class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        Allocation.objects.filter(resources__name='Slate Project').update(is_changeable=True)
