import logging
import os

from django.contrib.auth.models import User

from coldfront.core.subscription.models import Subscription, SubscriptionUser
from coldfront.core.subscription.utils import \
    set_subscription_user_status_to_error
from ipalib import api
from coldfront.plugins.freeipa.utils import check_ipa_group_error, UNIX_GROUP_ATTRIBUTE_NAME, \
                                           FREEIPA_NOOP, CLIENT_KTNAME, AlreadyMemberError, \
                                           NotMemberError, ApiError

logger = logging.getLogger(__name__)

def add_user_group(subscription_user_pk):
    subscription_user = SubscriptionUser.objects.get(pk=subscription_user_pk)
    if subscription_user.subscription.status.name != 'Active':
        logger.warn("Subscription is not active. Will not add groups")
        return

    if subscription_user.status.name != 'Active':
        logger.warn("Subscription user status is not 'Active'. Will not add groups.")
        return

    groups = subscription_user.subscription.get_attribute_list(UNIX_GROUP_ATTRIBUTE_NAME)
    if len(groups) == 0:
        logger.info("Subscription does not have any groups. Nothing to add")
        return

    os.environ["KRB5_CLIENT_KTNAME"] = CLIENT_KTNAME
    for g in groups:
        if FREEIPA_NOOP:
            logger.warn("NOOP - FreeIPA adding user %s to group %s", subscription_user.user.username, g)
            continue

        try:
            res = api.Command.group_add_member(g, user=[subscription_user.user.username])
            check_ipa_group_error(res)
        except AlreadyMemberError as e:
            logger.warn("User %s is already a member of group %s", subscription_user.user.username, g)
        except Exception as e:
            logger.error("Failed adding user %s to group %s: %s", subscription_user.user.username, g, e)
            set_subscription_user_status_to_error(subscription_user_pk)
        else:
            logger.info("Added user %s to group %s successfully", subscription_user.user.username, g)

def remove_user_group(subscription_user_pk):
    subscription_user = SubscriptionUser.objects.get(pk=subscription_user_pk)
    if subscription_user.subscription.status.name not in ['Active', 'Pending', 'Inactive (Renewed)', ]:
        logger.warn("Subscription is not active or pending. Will not remove groups.")
        return

    if subscription_user.status.name != 'Removed':
        logger.warn("Subscription user status is not 'Removed'. Will not remove groups.")
        return

    groups = subscription_user.subscription.get_attribute_list(UNIX_GROUP_ATTRIBUTE_NAME)
    if len(groups) == 0:
        logger.info("Subscription does not have any groups. Nothing to remove")
        return

    # Check other active subscriptions the user is active on for FreeIPA groups
    # and ensure we don't remove them.
    user_subs = Subscription.objects.filter(
        subscriptionuser__user=subscription_user.user,
        subscriptionuser__status__name='Active',
        status__name='Active',
        subscriptionattribute__subscription_attribute_type__name=UNIX_GROUP_ATTRIBUTE_NAME
    ).exclude(pk=subscription_user.subscription.pk).distinct()

    exclude = []
    for s in user_subs:
        for g in s.get_attribute_list(UNIX_GROUP_ATTRIBUTE_NAME):
            if g in groups:
                exclude.append(g)

    for g in exclude:
        groups.remove(g)

    if len(groups) == 0:
        logger.info("No groups to remove. User may belong to these groups in other active subscriptions: %s", exclude)
        return

    os.environ["KRB5_CLIENT_KTNAME"] = CLIENT_KTNAME
    for g in groups:
        if FREEIPA_NOOP:
            logger.warn("NOOP - FreeIPA removing user %s from group %s", subscription_user.user.username, g)
            continue

        try:
            res = api.Command.group_remove_member(g, user=[subscription_user.user.username])
            check_ipa_group_error(res)
        except NotMemberError as e:
            logger.warn("User %s is not a member of group %s", subscription_user.user.username, g)
        except Exception as e:
            logger.error("Failed removing user %s from group %s: %s", subscription_user.user.username, g, e)
            set_subscription_user_status_to_error(subscription_user_pk)
        else:
            logger.info("Removed user %s from group %s successfully", subscription_user.user.username, g)
