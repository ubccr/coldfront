from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
import logging


"""An admin command that creates primary email addresses for users that
have none."""


class Command(BaseCommand):

    help = (
        'Create a primary, verified EmailAddress for each User with zero '
        'associated EmailAddress objects. This script is intended for '
        'one-time use for existing users loaded in from spreadsheets.')
    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        # TODO: Remove this once all emails are transitioned to
        # TODO: allauth.account.models.EmailAddress.
        parser.add_argument(
            'module',
            choices=['allauth.account.models', 'coldfront.core.user.models'],
            help=(
                'There are temporarily two EmailAddress models, until all can '
                'be transitioned under allauth.account.models.'),
            type=str)

    def handle(self, *args, **options):
        """For each User that has no EmailAddress, create a verified,
        primary instance using the User's email field."""
        if options['module'] == 'allauth.account.models':
            from allauth.account.models import EmailAddress
            verified_field, primary_field = 'verified', 'primary'
        else:
            from coldfront.core.user.models import EmailAddress
            verified_field, primary_field = 'is_verified', 'is_primary'

        user_pks_with_emails = EmailAddress.objects.values_list(
            'user', flat=True)
        users_without_emails = User.objects.exclude(
            pk__in=user_pks_with_emails)

        for user in users_without_emails:
            email = user.email.lower()
            kwargs = {
                'user': user,
                'email': email,
                verified_field: True,
                primary_field: True,
            }
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
