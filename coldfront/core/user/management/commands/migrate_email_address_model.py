import logging
import sys
import traceback

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from allauth.account.models import EmailAddress as NewEmailAddress

from coldfront.core.user.models import EmailAddress as OldEmailAddress
from coldfront.core.utils.common import add_argparse_dry_run_argument


"""An admin command that creates or updates corresponding instances of
allauth.account.models.EmailAddress for existing emails in the User
model and coldfront.core.user.models.EmailAddress model."""


class Command(BaseCommand):

    help = (
        'Create or update instances of allauth.account.models.EmailAddress '
        'based on emails stored in the User model and the deprecated '
        'coldfront.core.users.models.EmailAddress model. This command strictly '
        'updates whether an email is primary or verified from False to True, '
        'and never the other way around (i.e., it respects existing values in '
        'the new model). It is intended for a one-time migration, and may not '
        'be suited for general reuse.')

    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        add_argparse_dry_run_argument(parser)

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        if not dry_run:
            user_confirmation = input(
                'Are you sure you wish to proceed? [Y/y/N/n]: ')
            if user_confirmation.strip().lower() != 'y':
                self.stdout.write(self.style.WARNING('Migration aborted.'))
                sys.exit(0)
        for user in User.objects.iterator():
            try:
                old_email_data = self._get_old_email_data(user)
                self._process_emails_for_user(
                    user, old_email_data, dry_run=dry_run)
            except Exception:
                message = (
                    f'Failed to process User {user.pk}. Details:\n'
                    f'{traceback.format_exc()}')
                self.stdout.write(self.style.ERROR(message))

    def _create_address_for_user(self, email, user, primary=False,
                                 verified=False, dry_run=True):
        """Create an instance of the new EmailAddress model for the
        given email (str) and User, setting its primary and verified
        fields. Optionally display the update instead of performing it.

        If the email already belongs to a different user, raise an
        error.

        This method makes the following assumptions:
            - The User does not already have a corresponding instance.
            - If primary is True, the User does not already have a
              primary instance.

        It should not be called if the assumptions are not true.
        """
        try:
            other_user_address = NewEmailAddress.objects.get(email=email)
        except NewEmailAddress.DoesNotExist:
            if dry_run:
                phrase = 'Would create'
                pk = 'PK'
                style = self.style.WARNING
            else:
                email_address = NewEmailAddress.objects.create(
                    user=user,
                    email=email,
                    primary=primary,
                    verified=verified)
                phrase = 'Created'
                pk = email_address.pk
                style = self.style.SUCCESS

            message = (
                f'{phrase} EmailAddress {pk} for User {user.pk} '
                f'({user.username}) with primary={primary} and '
                f'verified={verified}.')
            self.stdout.write(style(message))
            if not dry_run:
                self.logger.info(message)
        else:
            message = (
                f'A different User {other_user_address.user.pk} already has '
                f'email "{email}".')
            self.stdout.write(self.style.WARNING(message))
            if not dry_run:
                self.logger.warning(message)

    @staticmethod
    def _get_old_email_data(user):
        """Return a dict mapping emails (str) for the given User from
        the old model and the User instance to a dict with keys
        'primary' and 'verified', denoting whether the address was
        primary and verified.

        The email stored in the User instance is interpreted as being
        primary.

        Raise an error if the User does not have exactly one primary
        email under the old model.
        """
        old_addresses = OldEmailAddress.objects.filter(user=user)
        old_emails = {}

        for old_address in old_addresses:
            email_str = old_address.email.strip().lower()
            old_emails[email_str] = {
                'verified': old_address.is_verified,
                'primary': old_address.is_primary,
            }
        user_email_str = user.email.strip().lower()
        if user_email_str:
            if user_email_str in old_emails:
                old_emails[user_email_str]['primary'] = True
            else:
                old_emails[user_email_str] = {
                    'verified': False,
                    'primary': True,
                }

        old_primaries = []
        for email, attributes in old_emails.items():
            if attributes['primary']:
                old_primaries.append(email)

        num_primaries = len(old_primaries)
        if num_primaries == 0:
            raise Exception(
                f'Found no old primary emails for User {user.pk} '
                f'({user.username}).')
        elif num_primaries == 1:
            pass
        else:
            raise Exception(
                f'Found multiple old primary emails for User {user.pk} '
                f'({user.username}): {", ".join(old_primaries)}.')

        return old_emails

    def _process_emails_for_user(self, user, old_email_data, dry_run=True):
        """Given a User and a dict containing information about emails
        in the old model, create or update emails in the new model.
        Optionally display updates instead of performing them.

        old_email_data is assumed to contain exactly one primary
        address.
        """
        new_addresses = NewEmailAddress.objects.filter(user=user)
        new_address_lower_strs = set(
            [email.lower()
             for email in new_addresses.values_list('email', flat=True)])

        try:
            new_primary = new_addresses.get(primary=True)
        except NewEmailAddress.DoesNotExist:
            new_primary = None
        except NewEmailAddress.MultipleObjectsReturned as e:
            raise e

        for old_email, attributes in old_email_data.items():
            # If this was a primary address, but the user already has a
            # different primary, do not set this as primary.
            if attributes['primary']:
                if (new_primary is not None and
                        new_primary.email.lower() != old_email):
                    attributes['primary'] = False
            if old_email in new_address_lower_strs:
                email_address = new_addresses.get(email=old_email)
                self._update_address_for_user(
                    email_address, user, primary=attributes['primary'],
                    verified=attributes['verified'], dry_run=dry_run)
            else:
                self._create_address_for_user(
                    old_email, user, primary=attributes['primary'],
                    verified=attributes['verified'], dry_run=dry_run)

    def _update_address_for_user(self, email_address, user, primary=False,
                                 verified=False, dry_run=True):
        """Update the given EmailAddress instance (new model) for the
        given User, setting its primary and verified fields.

        It only sets fields if they would go from False to True.

        This method makes the following assumptions:
            - If primary is True, the User does not already have a
              primary instance other than the given instance.

        It should not be called if the assumptions are not true.
        """
        # Only update "primary" if it would go from False to True, not
        # the other way around.
        primary_updated = not email_address.primary and primary
        if primary_updated:
            email_address.primary = True
        # Only update "verified" if it would go from False to True, not
        # the other way around.
        verified_updated = not email_address.verified and verified
        if verified_updated:
            email_address.verified = True

        if primary_updated or verified_updated:
            if dry_run:
                phrase = 'Would update'
                style = self.style.WARNING
            else:
                email_address.save()
                phrase = 'Updated'
                style = self.style.SUCCESS

            updates = []
            if primary_updated:
                updates.append('set primary to True')
            if verified_updated:
                updates.append('set verified to True')

            message = (
                f'{phrase} EmailAddress {email_address.pk} '
                f'({email_address.email}) for User {user.pk} '
                f'({user.username}): {", ".join(updates)}.')
            self.stdout.write(style(message))
            if not dry_run:
                self.logger.info(message)
