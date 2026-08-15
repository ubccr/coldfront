# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.db.models.signals import post_save
from django.dispatch import Signal

group_membership_changed = Signal()


def create_userconfig(instance, created, raw=False, **kwargs):
    """
    Automatically create a new UserConfig when a new User is created.
    Skip this if importing a user from a fixture.
    """
    from coldfront.users.models import UserConfig

    if created and not raw:
        UserConfig(user=instance).save()


def connect_signals():
    """
    Connect signals to avoid circular imports during model loading.
    Called from apps.py ready() after models are registered.
    """
    from django.dispatch import receiver

    from coldfront.users.models import User

    @receiver(post_save, sender=User)
    def _create_userconfig(sender, instance, created, raw=False, **kwargs):
        create_userconfig(instance, created, raw=raw)
