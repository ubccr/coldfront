# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import os

from ipalib import api

from coldfront.core.allocation.models import Allocation, AllocationUser
from coldfront.core.allocation.utils import set_allocation_user_status_to_error
from coldfront.plugins.freeipa.utils import (
    CLIENT_KTNAME,
    FREEIPA_NOOP,
    UNIX_GROUP_ATTRIBUTE_NAME,
    AlreadyMemberError,
    NotMemberError,
    check_ipa_group_error,
)

logger = logging.getLogger(__name__)


def add_user_group(allocation_user_pk):
    allocation_user = AllocationUser.objects.get(pk=allocation_user_pk)
    if allocation_user.allocation.status.name != "Active":
        logger.warning("Allocation is not active. Will not add groups")
        return

    if allocation_user.status.name != "Active":
        logger.warning("Allocation user status is not 'Active'. Will not add groups.")
        return

    groups = allocation_user.allocation.get_attribute_list(UNIX_GROUP_ATTRIBUTE_NAME)
    if len(groups) == 0:
        logger.info("Allocation does not have any groups. Nothing to add")
        return

    os.environ["KRB5_CLIENT_KTNAME"] = CLIENT_KTNAME
    for g in groups:
        if FREEIPA_NOOP:
            logger.warning(
                "NOOP - FreeIPA adding user %s to group %s for allocation %s",
                allocation_user.user.username,
                g,
                allocation_user.allocation,
            )
            continue

        try:
            res = api.Command.group_add_member(g, user=[allocation_user.user.username])
            check_ipa_group_error(res)
        except AlreadyMemberError:
            logger.warning("User %s is already a member of group %s", allocation_user.user.username, g)
        except Exception as e:
            logger.error("Failed adding user %s to group %s: %s", allocation_user.user.username, g, e)
            set_allocation_user_status_to_error(allocation_user_pk)
        else:
            logger.info("Added user %s to group %s successfully", allocation_user.user.username, g)


def remove_user_group(allocation_user_pk):
    allocation_user = AllocationUser.objects.get(pk=allocation_user_pk)
    if allocation_user.allocation.status.name not in [
        "Active",
        "Pending",
        "Inactive (Renewed)",
    ]:
        logger.warning("Allocation is not active or pending. Will not remove groups.")
        return

    if allocation_user.status.name != "Removed":
        logger.warning("Allocation user status is not 'Removed'. Will not remove groups.")
        return

    groups = allocation_user.allocation.get_attribute_list(UNIX_GROUP_ATTRIBUTE_NAME)
    if len(groups) == 0:
        logger.info("Allocation does not have any groups. Nothing to remove")
        return

    # Check other active allocations the user is active on for FreeIPA groups
    # and ensure we don't remove them.
    user_allocations = (
        Allocation.objects.filter(
            allocationuser__user=allocation_user.user,
            allocationuser__status__name="Active",
            status__name="Active",
            allocationattribute__allocation_attribute_type__name=UNIX_GROUP_ATTRIBUTE_NAME,
        )
        .exclude(pk=allocation_user.allocation.pk)
        .distinct()
    )

    exclude = []
    for a in user_allocations:
        for g in a.get_attribute_list(UNIX_GROUP_ATTRIBUTE_NAME):
            if g in groups:
                exclude.append(g)

    for g in exclude:
        groups.remove(g)

    if len(groups) == 0:
        logger.info("No groups to remove. User may belong to these groups in other active allocations: %s", exclude)
        return

    os.environ["KRB5_CLIENT_KTNAME"] = CLIENT_KTNAME
    for g in groups:
        if FREEIPA_NOOP:
            logger.warning(
                "NOOP - FreeIPA removing user %s from group %s for allocation %s",
                allocation_user.user.username,
                g,
                allocation_user.allocation,
            )
            continue

        try:
            res = api.Command.group_remove_member(g, user=[allocation_user.user.username])
            check_ipa_group_error(res)
        except NotMemberError:
            logger.warning("User %s is not a member of group %s", allocation_user.user.username, g)
        except Exception as e:
            logger.error("Failed removing user %s from group %s: %s", allocation_user.user.username, g, e)
            set_allocation_user_status_to_error(allocation_user_pk)
        else:
            logger.info("Removed user %s from group %s successfully", allocation_user.user.username, g)
