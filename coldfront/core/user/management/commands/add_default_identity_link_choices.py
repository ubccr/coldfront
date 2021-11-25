import os

from django.core.management.base import BaseCommand
from coldfront.core.user.models import IdentityLinkingRequestStatusChoice


class Command(BaseCommand):
    help = 'Add default identiy linking request choices'

    def handle(self, *args, **options):
        for choice in ['Pending', 'Complete']:
            IdentityLinkingRequestStatusChoice.objects.get_or_create(name=choice)
