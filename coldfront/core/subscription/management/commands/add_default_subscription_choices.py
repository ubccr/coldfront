from django.core.management.base import BaseCommand

from coldfront.core.subscription.models import (SubscriptionStatusChoice,
                                                 SubscriptionUserStatusChoice)


class Command(BaseCommand):
    help = 'Add default subscription related choices'

    def handle(self, *args, **options):

        for choice in ('Active', 'Expired', 'Denied', 'Revoked', 'Unpaid', 'New', 'Renew Requested', ):
            SubscriptionStatusChoice.objects.get_or_create(name=choice)

        for choice in ('Active', 'Removed', 'Error'):
            SubscriptionUserStatusChoice.objects.get_or_create(name=choice)
