import os
import logging
import shlex
import subprocess

from django.contrib.auth.models import User
from django.db.models import Q
from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist

from common.djangolibs.utils import import_from_settings
from core.djangoapps.subscription.models import SubscriptionUser
from core.djangoapps.subscription.utils import \
    set_subscription_user_status_to_error

SLURM_CLUSTER_ATTRIBUTE_NAME = import_from_settings('SLURM_CLUSTER_ATTRIBUTE_NAME', 'slurm_cluster')
SLURM_ACCOUNT_ATTRIBUTE_NAME = import_from_settings('SLURM_ACCOUNT_ATTRIBUTE_NAME', 'slurm_account_name')
SLURM_NOOP = import_from_settings('SLURM_NOOP', False)
SLURM_SACCTMGR_PATH = import_from_settings('SLURM_SACCTMGR_PATH', '/usr/bin/sacctmgr')
SLURM_CMD_REMOVE_USER = SLURM_SACCTMGR_PATH + ' -Q -i delete user where name={} cluster={} account={}'

logger = logging.getLogger(__name__)

def _remove_assoc(user, cluster, account):
    cmd = SLURM_CMD_REMOVE_USER.format(user, cluster, account)

    if SLURM_NOOP:
        logger.info('NOOP - Slurm cmd: %s', cmd)
        return

    result = subprocess.run(shlex.split(cmd), stdout=subprocess.PIPE)
    if result.returncode != 0:
        logger.error('Slurm command failed: %s', cmd)
        err_msg = 'return_value={} output={}'.format(result.returncode, result.stdout)
        raise Exception(err_msg)

def remove_association(subscription_user_pk):
    subscription_user = SubscriptionUser.objects.get(pk=subscription_user_pk)
    if subscription_user.subscription.status.name not in ['Active', 'Pending', 'Inactive (Renewed)', ]:
        logger.warn("Subscription is not active or pending. Will not remove Slurm associations.")
        return

    try:
        slurm_account = subscription_user.subscription.subscriptionattribute_set.get(subscription_attribute_type__name=SLURM_ACCOUNT_ATTRIBUTE_NAME)
    except ObjectDoesNotExist:
        logger.warn("No slurm account name found for subscription: %s. Nothing to do.", subscription_user.subscription)
        return

    slurm_resources = subscription_user.subscription.resources.filter(
            Q(resourceattribute__resource_attribute_type__name=SLURM_CLUSTER_ATTRIBUTE_NAME) | 
            Q(parent_resource__resourceattribute__resource_attribute_type__name=SLURM_CLUSTER_ATTRIBUTE_NAME))

    for r in slurm_resources.distinct():
        cluster_name = None
        try:
            cluster_name = r.resourceattribute_set.get(resource_attribute_type__name='slurm_cluster')
        except ObjectDoesNotExist:
            try:
                cluster_name = r.parent_resource.resourceattribute_set.get(resource_attribute_type__name='slurm_cluster')
            except ObjectDoesNotExist:
                pass

        if not cluster_name:
            logger.error("Could not find cluster name for resource %s for subscription %s", r, subscription_user.subscription)
            continue

        try:
            _remove_assoc(subscription_user.user.username, cluster_name.value, slurm_account.value)
        except Exception as e:
            logger.error("Failed removing Slurm assocation for user %s on account %s in cluster %s: %s", subscription_user.user.username, slurm_account.value, cluster_name.value, e)
            set_subscription_user_status_to_error(subscription_user_pk)
        else:
            logger.info("Successfully removed Slurm assocation: user=%s cluster=%s account=%s", subscription_user.user.username, cluster_name.value, slurm_account.value)
