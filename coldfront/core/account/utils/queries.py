from django.db import transaction

from allauth.account.models import EmailAddress

import logging


logger = logging.getLogger(__name__)


def update_user_primary_email_address(email_address):
    """Given an EmailAddress, which must be verified, perform the
    following:
        - If the user's current email field does not have a
          corresponding EmailAddress, create one (verified);
        - Set the user's email field to it;
        - Set it as the primary EmailAddress of the user; and
        - Set the user's other EmailAddress objects to be non-primary.

    Perform the updates in a transaction so that they all fail together
    or all succeed together.

    Parameters:
        - email_address (EmailAddress): the EmailAddress object to set
                                        as the new primary

    Returns:
        - None

    Raises:
        - TypeError, if the provided address has an invalid type
        - ValueError, if the provided address is not verified
    """
    if not isinstance(email_address, EmailAddress):
        raise TypeError(f'Invalid EmailAddress {email_address}.')
    if not email_address.verified:
        raise ValueError(f'EmailAddress {email_address} is unverified.')

    user = email_address.user
    with transaction.atomic():

        old_primary, created = EmailAddress.objects.get_or_create(
            user=user, email=user.email.lower())
        if created:
            message = (
                f'Created EmailAddress {old_primary.pk} for User {user.pk}\'s '
                f'old primary address {old_primary.email}, which unexpectedly '
                f'did not exist.')
            logger.warning(message)
        old_primary.verified = True
        old_primary.primary = False
        old_primary.save()

        # TODO: Hide behind feature flag? This seems relevant no matter what.
        for ea in EmailAddress.objects.filter(
                user=user, primary=True).exclude(pk=email_address.pk):
            ea.primary = False
            ea.save()

        user.email = email_address.email
        user.save()

        email_address.primary = True
        email_address.save()
