import time

from django.core.management.base import BaseCommand
from coldfront.core.allocation.models import AllocationUserStatusChoice, AllocationUser


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument("--old", type=str, required=True)
        parser.add_argument("--new", type=str, required=True)

    def handle(self, *args, **kwargs):
        old = AllocationUserStatusChoice.objects.get(name=kwargs.get("old"))
        new = AllocationUserStatusChoice.objects.get(name=kwargs.get("new"))

        AllocationUser.objects.filter(allocation__resources__name='Slate Project', status=old).update(status=new)
