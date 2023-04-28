from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from allauth.account.models import EmailAddress

import logging


"""An admin command that creates primary email addresses for users that
have none."""


class Command(BaseCommand):

    help = (
        'Create a primary, verified EmailAddress for each User with zero '
        'associated EmailAddress objects. This script is intended for '
        'one-time use for existing users loaded in from spreadsheets.')
    logger = logging.getLogger(__name__)

    def handle(self, *args, **options):
        """For each User that has no EmailAddress, create a verified,
        primary instance using the User's email field."""
        user_pks_with_emails = EmailAddress.objects.values_list(
            'user', flat=True)
        users_without_emails = User.objects.exclude(
            pk__in=user_pks_with_emails)

        for user in users_without_emails:
            email = user.email.lower()
            kwargs = {
                'user': user,
                'email': email,
                'verified': True,
                'primary': True,
            }
            if not email:
                message = f'User {user.pk} email is empty.'
                self.stderr.write(self.style.ERROR(message))
                continue
            try:
                email_address = EmailAddress.objects.create(**kwargs)
            except Exception as e:
                message = (
                    f'Failed to create a verified, primary EmailAddress for '
                    f'User {user.pk} and email {email}. Details:\n{e}')
                self.stderr.write(self.style.ERROR(message))
            else:
                message = (
                    f'Created verified, primary EmailAddress '
                    f'{email_address.pk} for User {user.pk} and email '
                    f'{email}.')
                self.logger.info(message)
