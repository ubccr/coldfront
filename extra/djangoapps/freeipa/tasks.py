import logging
import os

from django.contrib.auth.models import User

from core.djangoapps.subscription.models import SubscriptionUser
from core.djangoapps.subscription.utils import \
    set_subscription_user_status_to_error
from ipalib import api
from extra.djangoapps.freeipa.utils import check_ipa_group_error, UNIX_GROUP_ATTRIBUTE_NAME, CLIENT_KTNAME

logger = logging.getLogger(__name__)

def add_user_group(subscription_user_pk):
    subscription_user = SubscriptionUser.objects.get(pk=subscription_user_pk)
    if subscription_user.subscription.status.name != 'Active':
        logger.warn("Subscription is not active. Will not add groups")
        return

    groups = subscription_user.subscription.subscriptionattribute_set.filter(subscription_attribute_type__name=UNIX_GROUP_ATTRIBUTE_NAME)
    if len(groups) == 0:
        logger.info("Subscription does not have any groups. Nothing to add")
        return

    os.environ["KRB5_CLIENT_KTNAME"] = CLIENT_KTNAME
    for g in groups:
        try:
            res = api.Command.group_add_member(g.value, user=[subscription_user.user.username])
            check_ipa_group_error(res)
        except Exception as e:
            logger.error("Failed adding user %s to group %s: %s", subscription_user.user.username, g.value, e)
            set_subscription_user_status_to_error(subscription_user_pk)
        else:
            logger.info("Added user %s to group %s successfully", subscription_user.user.username, g.value)

def remove_user_group(subscription_user_pk):
    subscription_user = SubscriptionUser.objects.get(pk=subscription_user_pk)
    if subscription_user.subscription.status.name not in ['Active', 'Pending', 'Inactive (Renewed)', ]:
        logger.warn("Subscription is not active or pending. Will not remove groups.")
        return

    groups = subscription_user.subscription.subscriptionattribute_set.filter(subscription_attribute_type__name=UNIX_GROUP_ATTRIBUTE_NAME)
    if len(groups) == 0:
        logger.info("Subscription does not have any groups. Nothing to remove")
        return

    os.environ["KRB5_CLIENT_KTNAME"] = CLIENT_KTNAME
    for g in groups:
        try:
            res = api.Command.group_remove_member(g.value, user=[subscription_user.user.username])
            check_ipa_group_error(res)
        except Exception as e:
            logger.error("Failed removing user %s from group %s: %s", subscription_user.user.username, g.value, e)
            set_subscription_user_status_to_error(subscription_user_pk)
        else:
            logger.info("Removed user %s from group %s successfully", subscription_user.user.username, g.value)
