import logging
import os
import sys

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from core.djangoapps.subscription.models import Subscription
from extra.djangoapps.slurm.utils import slurm_check_assoc, slurm_remove_assoc, \
              slurm_add_assoc, SLURM_CLUSTER_ATTRIBUTE_NAME, \
              SLURM_ACCOUNT_ATTRIBUTE_NAME, SLURM_USER_SPECS_ATTRIBUTE_NAME

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Sync associations in Slurm'

    def add_arguments(self, parser):
        parser.add_argument("-s", "--sync", help="Sync changes to Slurm", action="store_true")
        parser.add_argument("-u", "--username", help="Check specific username")
        parser.add_argument("-a", "--account", help="Check specific account")
        parser.add_argument("-x", "--header", help="Include header in output", action="store_true")

    def add_assoc(self, userobj, cluster, account, specs=[]):
        if self.sync:
            try:
                slurm_add_assoc(userobj.user.username, cluster, account, specs=specs)
            except Exception as e:
                logger.error("Failed adding Slurm assocation for user %s on account %s in cluster %s: %s", userobj.user.username, account, cluster, e)
            else:
                logger.info("Successfully added Slurm assocation: user=%s cluster=%s account=%s", userobj.user.username, cluster, account)

        row = [
            userobj.user.username,
            str(userobj.subscription.id),
            userobj.status.name,
            cluster,
            account,
            'Add',
            ' '.join(specs) if specs else '',
        ]

        self.stdout.write('\t'.join(row))

    def remove_assoc(self, userobj, cluster, account):
        if self.sync:
            try:
                slurm_remove_assoc(userobj.user.username, cluster, account)
            except Exception as e:
                logger.error("Failed removing Slurm assocation for user %s on account %s in cluster %s: %s", userobj.user.username, account, cluster, e)
            else:
                logger.info("Successfully removed Slurm assocation: user=%s cluster=%s account=%s", userobj.user.username, cluster, account)

        row = [
            userobj.user.username,
            str(userobj.subscription.id),
            userobj.status.name,
            cluster,
            account,
            'Remove',
            '',
        ]

        self.stdout.write('\t'.join(row))

    def check_user(self, userobj, cluster, account, specs=[]):
        logger.info("Checking slurm association for user %s in subscription %s for slurm account %s on cluster %s", userobj.user.username, userobj.subscription, account, cluster)

        has_association = slurm_check_assoc(userobj.user.username, cluster, account)

        if userobj.status.name == 'Active' and not has_association:
            logger.warn('Active user %s does not have slurm assocation %s in cluster %s', userobj.user.username, account, cluster)
            self.add_assoc(userobj, cluster, account, specs=specs)
        elif userobj.status.name == 'Removed' and has_association:
            logger.warn('Removed user %s has slurm assocation %s in cluster %s', userobj.user.username, account, cluster)
            self.remove_assoc(userobj, cluster, account)

    def check_subscription(self, sub, filter_account=None, filter_user=None):
        slurm_account = sub.subscriptionattribute_set.filter(subscription_attribute_type__name=SLURM_ACCOUNT_ATTRIBUTE_NAME).first()
        if filter_account and filter_account != slurm_account.value:
            return

        specs = []
        user_specs = sub.subscriptionattribute_set.filter(subscription_attribute_type__name=SLURM_USER_SPECS_ATTRIBUTE_NAME).first()
        if user_specs and user_specs.value:
            specs = user_specs.value.split(':')

        slurm_resources = sub.resources.filter(
                Q(resourceattribute__resource_attribute_type__name=SLURM_CLUSTER_ATTRIBUTE_NAME) | 
                Q(parent_resource__resourceattribute__resource_attribute_type__name=SLURM_CLUSTER_ATTRIBUTE_NAME))

        for r in slurm_resources.distinct():
            cname = None
            try:
                cname = r.resourceattribute_set.get(resource_attribute_type__name=SLURM_CLUSTER_ATTRIBUTE_NAME)
            except:
                cname = r.parent_resource.resourceattribute_set.get(resource_attribute_type__name=SLURM_CLUSTER_ATTRIBUTE_NAME)

            if not cname:
                logger.error("Could not find cluster name from resource {} for subscription {}", r, s)
                continue
                    
            for u in sub.subscriptionuser_set.filter(status__name__in=['Active', 'Removed', ]):
                if filter_user and filter_user != u.user.username:
                    continue

                self.check_user(u, cname.value, slurm_account.value, specs=specs)

    def handle(self, *args, **options):
        verbosity = int(options['verbosity'])
        root_logger = logging.getLogger('')
        if verbosity == 0:
            root_logger.setLevel(logging.ERROR)
        elif verbosity == 2:
            root_logger.setLevel(logging.INFO)
        elif verbosity == 3:
            root_logger.setLevel(logging.DEBUG)
        else:
            root_logger.setLevel(logging.WARN)

        self.sync = False
        if options['sync']:
            self.sync = True
            logger.warn("Syncing Slurm with Coldfront")

        header = [
            'username',
            'subscription_id',
            'subscription_user_status',
            'cluster',
            'account',
            'action',
            'slurm_user_specs',
        ]

        if options['header']:
            self.stdout.write('\t'.join(header))

        # Fetch all active subscriptions with a 'slurm_account' attribute
        subs = Subscription.objects.prefetch_related(
                'project',
                'resources',
                'subscriptionattribute_set',
                'subscriptionuser_set'
            ).filter(
                status__name='Active',
                subscriptionattribute__subscription_attribute_type__name=SLURM_ACCOUNT_ATTRIBUTE_NAME,
            ).distinct()

        logger.info("Processing %s active subscriptions with %s attribute", len(subs), SLURM_ACCOUNT_ATTRIBUTE_NAME)
        if options['username']:
            logger.info("Filtering output by username: %s", options['username'])
        if options['account']:
            logger.info("Filtering output by slurm account: %s", options['account'])

        for s in subs:
            self.check_subscription(s, options['account'], options['username'])
