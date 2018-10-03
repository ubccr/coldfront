import sys
import os
import logging
from django.db.models import Q
from django.core.management.base import BaseCommand, CommandError
from core.djangoapps.subscription.models import Subscription
from core.djangoapps.resources.models import Resource,ResourceAttribute

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Dump slurm assocations for sacctmgr in flat file format'

    def add_arguments(self, parser):
        parser.add_argument("-o", "--output", help="Path to output directory")

    def write_cluster(self, out, cluster):
        """Write out Slurm assocations for the given cluster
        """
        # Fetch resource for given Slurm cluster
        try:
            r = Resource.objects.get(
                    is_available=True,
                    resourceattribute__resource_attribute_type__name='slurm_cluster',
                    resourceattribute__value=cluster,
                )
        except:
            logger.warn("No resource found for Slurm cluster: %s", cluster)
            return

        specs = r.resourceattribute_set.filter(resource_attribute_type__name='slurm_specs').first()
        out.write("Cluster - '{}':{}\n".format(
            cluster,
            specs.value if specs else '',
        ))
        out.write("Parent - 'root'\n")

    def write_account_user(self, out, username, specs):
        """Write out user assocation"""
        out.write("User - '{}':{}\n".format(
            username,
            specs.value if specs else '',
        ))

    def write_account_from_subscription(self, out, sub, specs=[]):
        """Write out account assocation"""
        try:
            slurm_account = sub.subscriptionattribute_set.get(subscription_attribute_type__name='slurm_account_name')
        except:
            logger.warn("No slurm account name found for subscription: %s", sub)
            return
            
        user_specs = sub.subscriptionattribute_set.filter(subscription_attribute_type__name='slurm_user_specs').first()
        sub_specs = sub.subscriptionattribute_set.filter(subscription_attribute_type__name='slurm_specs').first()
        if sub_specs:
            specs.append(sub_specs.value)

        out.write("Account - '{}':{}\n".format(
            slurm_account.value,
            ':'.join(specs)
        ))

        out.write("Parent - '{}'\n".format(slurm_account.value))
        for u in sub.subscriptionuser_set.filter(status__name='Active'):
            self.write_account_user(out, u.user.username, user_specs)

    def process_subscriptions(self):
        """Process all active subscriptions with a 'slurm_account_name'
           attribute and organize them by cluster. The name of the Slurm
           cluster is stored in a resource attribute named 'slurm_cluster' on
           the resource or it's parent
        """
        cluster_map = {}

        # Fetch all active subscriptions with a 'slurm_account_name' attribute
        subs = Subscription.objects.prefetch_related(
                'project',
                'resources',
                'subscriptionattribute_set',
                'subscriptionuser_set'
            ).filter(
                status__name='Active',
                subscriptionattribute__subscription_attribute_type__name='slurm_account_name',
            )

        # For each subscription, fetch the subscribed resources that have a
        # slurm_cluster attribute on itself or it's parent.
        for s in subs:

            slurm_resources = s.resources.filter(
                    Q(resourceattribute__resource_attribute_type__name='slurm_cluster') | 
                    Q(parent_resource__resourceattribute__resource_attribute_type__name='slurm_cluster'))

            for r in slurm_resources.distinct():
                specs = []
                cname = None
                try:
                    cname = r.resourceattribute_set.get(resource_attribute_type__name='slurm_cluster')
                except:
                    cname = r.parent_resource.resourceattribute_set.get(resource_attribute_type__name='slurm_cluster')

                if not cname:
                    logger.error("Could not find cluster name from resource {} for subscription {}", r, s)
                    continue

                # If resource_type is a slurm parition we merge the specs into the Slurm account association
                if r.resource_type.name == 'Cluster Partition':
                    rspecs = r.resourceattribute_set.filter(resource_attribute_type__name='slurm_specs').first()
                    if rspecs:
                        specs.append(rspecs.value) 

                rec = cluster_map.get(cname.value, {})
                rec[s] = rec.get(s, []) + specs
                cluster_map[cname.value] = rec 
        
        return cluster_map

    def handle(self, *args, **options):
        self.slurm_out = os.getcwd()
        if options['output']:
            self.slurm_out = options['output']

        if not os.path.isdir(self.slurm_out):
            os.mkdir(self.slurm_out, 0o0700)

        logger.warn("Writing output to directory: %s", self.slurm_out)

        cluster_map = self.process_subscriptions()

        if len(cluster_map) == 0:
            logger.warn("No subscriptions found to any Slurm resources. Nothing to do.")
            sys.exit(1)

        # Write out one file per Slurm cluster
        for cluster, subs in cluster_map.items():
            with open(os.path.join(self.slurm_out, '{}.cfg'.format(cluster)), 'w') as fh:
                self.write_cluster(fh, cluster)
                for sub, rspecs in subs.items():
                    self.write_account_from_subscription(fh, sub, specs=rspecs)
