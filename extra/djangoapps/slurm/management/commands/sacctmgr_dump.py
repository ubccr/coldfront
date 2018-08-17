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
        # Fetch all resources for given cluster
        resources = Resource.objects.filter(
                is_available=True,
                parent_resource=None,
                resourceattribute__resource_attribute_type__name='slurm_cluster',
                resourceattribute__value=cluster,
            )

        for r in resources:
            specs = r.resourceattribute_set.filter(resource_attribute_type__name='slurm_specs').first()
            out.write("Cluster - '{}':{}\n".format(
                cluster,
                specs.value if specs else '',
            ))
            out.write("Parent - 'root'\n")
            self.write_accounts(out, r)

            children = Resource.objects.filter(
                    is_available=True,
                    parent_resource=r,
                )
            for c in children:
                self.write_accounts(out, c)

    def write_accounts(self, out, resource):
        subs = resource.subscription_set.prefetch_related(
                'project',
                'subscriptionattribute_set',
                'subscriptionuser_set'
            ).filter(
                status__name='Active'
            )

        for s in subs:
            self.write_account_from_subscription(out, resource, s)

    def write_account_user(self, out, username, specs):
        """Write out user assocation"""
        out.write("User - '{}':{}\n".format(
            username,
            specs.value if specs else '',
        ))

    def write_account_from_subscription(self, out, resource, sub):
        """Write out account assocation"""
        specs = sub.subscriptionattribute_set.filter(subscription_attribute_type__name='slurm_specs').first()
        user_specs = sub.subscriptionattribute_set.filter(subscription_attribute_type__name='Slurm user specifications').first()
        slurm_account = sub.subscriptionattribute_set.filter(subscription_attribute_type__name='Slurm Account Name').first()
        if slurm_account is None:
            logger.warn("Subscription {} to resource {} is missing 'Slurm Account Name' attribute. Skipping".format(sub, resource))
            return

        out.write("Account - '{}':Description='{}':{}\n".format(
            slurm_account.value,
            sub.project.title.replace("'", '').strip(),
            specs.value if specs else '',
        ))

        out.write("Parent - '{}'\n".format(slurm_account.value))
        for u in sub.subscriptionuser_set.filter(status__name='Active'):
            self.write_account_user(out, u.user.username, user_specs)

    def handle(self, *args, **options):
        self.slurm_out = os.getcwd()
        if options['output']:
            self.slurm_out = options['output']

        if not os.path.isdir(self.slurm_out):
            os.mkdir(self.slurm_out, 0o0700)

        logger.warn("Writing output to directory: %s", self.slurm_out)

        # Fetch list of SLURM clusters
        clusters = ResourceAttribute.objects.filter(
                resource_attribute_type__name='slurm_cluster'
            )

        for cluster in clusters.distinct():
            with open(os.path.join(self.slurm_out, '{}.cfg'.format(cluster.value)), 'w') as fh:
                self.write_cluster(fh, cluster.value)
