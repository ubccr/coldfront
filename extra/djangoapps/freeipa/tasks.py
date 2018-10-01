import os
import logging

from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from ipalib import api

from common.djangolibs.utils import import_from_settings
from core.djangoapps.subscription.models import SubscriptionUser
from core.djangoapps.subscription.utils import \
    set_subscription_user_status_to_error

CLIENT_KTNAME = import_from_settings('FREEIPA_KTNAME')
UNIX_GROUP_ATTRIBUTE_NAME = import_from_settings('FREEIPA_GROUP_ATTRIBUTE_NAME', 'freeipa_group')

try:
    api.bootstrap()
    api.finalize()
    api.Backend.rpcclient.connect()
except Exception as e:
    logger.error("Failed to initialze FreeIPA lib: %s", e)
    raise ImproperlyConfigured('Failed to initialze FreeIPA: {0}'.format(e))

logger = logging.getLogger(__name__)

def check_ipa_group_error(res):
    if not res:
        raise ValueError('Missing FreeIPA response')

    if res['completed'] == 1:
        return

    user = res['failed']['member']['user'][0][0]
    group = res['result']['cn'][0]
    err_msg = res['failed']['member']['user'][0][1]

    # If user is already a member don't error out. Silently ignore
    if err_msg == 'This entry is already a member':
        logger.warn("User %s is already a member of group %s", user, group)
        return

    raise Exception(err_msg)

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
