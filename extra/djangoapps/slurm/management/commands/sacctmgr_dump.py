import sys
import os
import logging
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
        # Fetch resource for given cluster
        r = Resource.objects.filter(
                is_available=True,
                parent_resource=None,
                resourceattribute__resource_attribute_type__name='slurm_cluster',
                resourceattribute__value=cluster,
            ).first()

        if not r:
            logger.warn("No parent resource found for cluster: %s", cluster)
            return

        specs = r.resourceattribute_set.filter(resource_attribute_type__name='slurm_specs').first()
        out.write("Cluster - '{}':{}\n".format(
            cluster,
            specs.value if specs else '',
        ))
        out.write("Parent - 'root'\n")

    def write_accounts(self, out, subs):
        for s in subs:
            self.write_account_from_subscription(out, resource, s)

    def write_account_user(self, out, username, specs):
        """Write out user assocation"""
        out.write("User - '{}':{}\n".format(
            username,
            specs.value if specs else '',
        ))

    def write_account_from_subscription(self, out, sub, specs=[]):
        """Write out account assocation"""
        sub_specs = sub.subscriptionattribute_set.filter(subscription_attribute_type__name='slurm_specs').first()
        user_specs = sub.subscriptionattribute_set.filter(subscription_attribute_type__name='slurm_user_specs').first()
        slurm_account = sub.subscriptionattribute_set.filter(subscription_attribute_type__name='slurm_account_name').first()
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
        cluster_map = {}

        subs = Subscription.objects.prefetch_related(
                'project',
                'resources',
                'subscriptionattribute_set',
                'subscriptionuser_set'
            ).filter(
                status__name='Active',
                subscriptionattribute__subscription_attribute_type__name='slurm_account_name',
            )
        for s in subs:
            for r in s.resources.filter(resourceattribute__resource_attribute_type__name='slurm_cluster'):
                specs = []
                cname = r.resourceattribute_set.filter(resource_attribute_type__name='slurm_cluster').first()
                if r.parent_resource:
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
            logger.warn("No subscriptions found to any SLURM resources. Nothing to do.")
            sys.exit(1)

        for cluster, subs in cluster_map.items():
            with open(os.path.join(self.slurm_out, '{}.cfg'.format(cluster)), 'w') as fh:
                self.write_cluster(fh, cluster)
                for s, rspecs in subs.items():
                    self.write_account_from_subscription(fh, s, specs=rspecs)

        # Fetch list of SLURM clusters
#        clusters = ResourceAttribute.objects.filter(
#                resource_attribute_type__name='slurm_cluster'
#            )

#        for cluster in clusters.distinct():
#            with open(os.path.join(self.slurm_out, '{}.cfg'.format(cluster.value)), 'w') as fh:
#                self.write_cluster(fh, cluster.value)
