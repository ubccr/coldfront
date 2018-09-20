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

try:
    api.bootstrap()
    api.finalize()
    api.Backend.rpcclient.connect()
except Exception as e:
    logger.error("Failed to initialze FreeIPA lib: %s", e)
    raise ImproperlyConfigured('Failed to initialze FreeIPA: {0}'.format(e))

# Resource Name
# subscription_user_obj.subscription.resources.first().name

# Resource Type Name
# subscription_user_obj.subscription.resources.first().resource_type.name

# User groups
# subscription_user_obj.user.group_set.all()

logger = logging.getLogger(__name__)

def add_user_group(subscription_user_pk):
    subscription_user = SubscriptionUser.objects.get(pk=subscription_user_pk)
    freeipa_group = subscription_user.subscription.subscriptionattribute_set.filter(subscription_attribute_type__name='freeipa_group').first()
    if not freeipa_group:
        logger.info("Subscription does not have a group. Nothing to add")
        return

    os.environ["KRB5_CLIENT_KTNAME"] = CLIENT_KTNAME
    try:
        print(api.Command.user_show(u'ccruser'))
        logger.info("Added user %s to group %s successfully", subscription_user.user.username, freeipa_group.value)
    except Exception as e:
        logger.error("Failed adding user %s to group %s: %s", subscription_user.user.username, freeipa_group.value, e)
        set_subscription_user_status_to_error(subscription_user_pk)

def remove_user_group(subscription_user_pk):
    subscription_user = SubscriptionUser.objects.get(pk=subscription_user_pk)
    freeipa_group = subscription_user.subscription.subscriptionattribute_set.filter(subscription_attribute_type__name='freeipa_group').first()
    if not freeipa_group:
        logger.info("Subscription does not have a group. Nothing to remove")
        return

    os.environ["KRB5_CLIENT_KTNAME"] = CLIENT_KTNAME
    try:
        print(api.Command.user_show(u'jbednasz'))
        logger.info("Removed user %s from group %s successfully", subscription_user.user.username, freeipa_group.value)
    except Exception as e:
        logger.error("Failed removing user %s from group %s: %s", subscription_user.user.username, freeipa_group.value, e)
        set_subscription_user_status_to_error(subscription_user_pk)
