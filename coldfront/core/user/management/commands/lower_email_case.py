from coldfront.core.user.models import EmailAddress
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
import logging


"""An admin command that modifies emails stored in the User and
EmailAddress models so that they are in lowercase."""


class Command(BaseCommand):

    help = (
        'Update email addresses so that they are stored in lowercase.')
    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        """For each User and EmailAddress with an email field that has
        an uppercase character, convert it to lowercase."""
        for user in User.objects.all():
            email = user.email
            if any(c.isupper() for c in email):
                user.email = email.lower()
                user.save()
                message = (
                    f'Changed User {user.pk}\'s email from {email} to '
                    f'{user.email}.')
                self.stdout.write(self.style.SUCCESS(message))
                self.logger.info(message)
            username = user.username
            if any(c.isupper() for c in username):
                user.username = username.lower()
                user.save()
                message = (
                    f'Changed User {user.pk}\'s username from {username} to '
                    f'{user.username}.')
                self.stdout.write(self.style.SUCCESS(message))
                self.logger.info(message)
        for email_address in EmailAddress.objects.all():
            email = email_address.email
            if any(c.isupper() for c in email):
                email_address.email = email.lower()
                email_address.save()
                message = (
                    f'Changed EmailAddress {email_address.pk}\'s email from '
                    f'{email} to {email_address.email}.')
                self.stdout.write(self.style.SUCCESS(message))
                self.logger.info(message)
