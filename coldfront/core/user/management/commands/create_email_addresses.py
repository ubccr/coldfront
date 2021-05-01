from coldfront.core.user.models import EmailAddress
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
import logging


"""An admin command that creates primary email addresses for users that
have none."""


class Command(BaseCommand):

    help = (
        'Create a primary EmailAddress for each User with zero '
        'associated EmailAddress objects.')
    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        """For each User that has no EmailAddress, create one with
        is_primary set to True."""
        users = User.objects.prefetch_related(
            'emailaddress_set').filter(emailaddress=None)
        for user in users:
            # Leave the EmailAddress as unverified. In most cases, it will
            # be verified during initial account activation.
            email = user.email.lower()
            email_address = EmailAddress.objects.create(
                user=user,
                email=email,
                is_verified=False,
                is_primary=True)
            message = (
                f'Created unverified, primary EmailAddress {email_address.pk} '
                f'for User {user.pk} and email {email}.')
            self.logger.info(message)
