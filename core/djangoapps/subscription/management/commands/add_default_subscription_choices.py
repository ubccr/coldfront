from django.core.management.base import BaseCommand

from core.djangoapps.subscription.models import (SubscriptionStatusChoice,
                                                 SubscriptionUserStatusChoice)


class Command(BaseCommand):
    help = 'Add default subscription related choices'

    def handle(self, *args, **options):

        for choice in ('Active', 'Pending', 'Expired', 'Denied', 'Revoked', 'Unpaid', 'New', 'Inactive (Renewed)', 'Approved'):
            SubscriptionStatusChoice.objects.get_or_create(name=choice)

        for choice in ('Active', 'Denied', 'Pending - Add', 'Pending - Remove', 'Removed', 'Error'):
            SubscriptionUserStatusChoice.objects.get_or_create(name=choice)
