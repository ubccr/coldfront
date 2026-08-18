# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import Signal, receiver

from coldfront.users.models import User, UserConfig

group_membership_changed = Signal()


@receiver(post_save, sender=User)
def create_userconfig(instance, created, raw=False, **kwargs):
    """
    Automatically create a new UserConfig when a new User is created.
    Skip this if importing a user from a fixture.
    """

    if created and not raw:
        UserConfig(user=instance, data=settings.DEFAULT_USER_PREFERENCES).save()
