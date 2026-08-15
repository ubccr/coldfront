# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import logging

from django.conf import settings
from django.contrib.auth import get_user_model

from coldfront.users.models import Group

__all__ = (
    "user_default_groups_handler",
    "match_user_by_username",
    "sync_user_groups",
)


User = get_user_model()


def match_user_by_username(strategy, details, user=None, *args, **kwargs):
    # If the user is already found or authenticated, move to the next step
    if user:
        return {"user": user}

    # Grab the username parsed from the OIDC claim
    username = details.get("username")

    if username:
        try:
            # Look for the existing user in your database
            existing_user = User.objects.get(username=username)
            return {"user": existing_user}
        except User.DoesNotExist:
            pass

    return None


def user_default_groups_handler(backend, user, response, *args, **kwargs):
    """
    Custom pipeline handler which adds remote auth users to the default group specified in the
    configuration file.
    """
    logger = logging.getLogger("coldfront.auth.user_default_groups_handler")
    if settings.REMOTE_AUTH_DEFAULT_GROUPS:
        # Assign default groups to the user
        group_list = []
        for name in settings.REMOTE_AUTH_DEFAULT_GROUPS:
            try:
                group_list.append(Group.objects.get(name=name))
            except Group.DoesNotExist:
                logging.error(f"Could not assign group {name} to remotely-authenticated user {user}: Group not found")
        if group_list:
            user.groups.add(*group_list)
        else:
            logger.info(f"No valid group assignments for {user} - REMOTE_AUTH_DEFAULT_GROUPS may be incorrectly set?")


def sync_user_groups(backend, user, response, *args, **kwargs):
    """
    Syncs identity provider groups with ColdFront groups.
    """
    if not settings.SOCIAL_AUTH_MIRROR_GROUPS:
        return

    idp_groups = response.get("groups", [])

    if not isinstance(idp_groups, list):
        return

    user.groups.clear()

    for group_name in idp_groups:
        group, created = Group.objects.get_or_create(name=group_name)
        user.groups.add(group)
