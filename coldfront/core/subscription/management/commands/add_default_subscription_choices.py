from django.core.management.base import BaseCommand

from coldfront.core.subscription.models import (SubscriptionStatusChoice,
                                                 SubscriptionUserStatusChoice)


class Command(BaseCommand):
    help = 'Add default subscription related choices'

    def handle(self, *args, **options):

        for choice in ('Active', 'Denied', 'Expired', 'New', 'Renew Requested', 'Revoked', 'Unpaid',):
            SubscriptionStatusChoice.objects.get_or_create(name=choice)

        for choice in ('Active', 'Error', 'Removed', ):
            SubscriptionUserStatusChoice.objects.get_or_create(name=choice)
