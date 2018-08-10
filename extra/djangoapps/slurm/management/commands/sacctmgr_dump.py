from django.core.management.base import BaseCommand, CommandError
from core.djangoapps.subscription.models import Subscription
from core.djangoapps.resources.models import Resource
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Dump slurm assocations for sacctmgr in flat file format'

    def add_arguments(self, parser):
        parser.add_argument("-o", "--output", help="Path to output file (defaults to STDOUT)")

    def write_resource(self, cluster, qos):
        """Write out Cluster. Anything included on this line will be the defaults
        for all associations on this cluster
        """
        self.slurm_out.write("Cluster - '{}':Fairshare=1:QOS='{}'\n".format(
            cluster,
            ','.join(list(set(qos))),
        ))

    def write_account_user(self, account, username):
        """Write out user assocation"""
        self.slurm_out.write("User - '{}':DefaultAccount='{}'\n".format(
            username,
            account,
        ))

    def write_account_from_subscription(self, resource, sub):
        """Write out account assocation"""
        sub_qos = sub.subscriptionattribute_set.filter(subscription_attribute_type__name='Slurm QOS').first()
        qos = []
        if sub_qos is not None:
            qos += sub_qos.value.split(',')

        slurm_account = sub.subscriptionattribute_set.filter(subscription_attribute_type__name='Slurm Account Name').first()
        if slurm_account is None:
            logger.warn("Subscription {} to resource {} is missing 'Slurm Account Name' attribute. Skipping".format(sub, resource))
            return

        self.slurm_out.write("Account - '{}':Description='{}':Fairshare=100:QOS='{}'\n".format(
            slurm_account.value,
            sub.project.title.replace("'", '').strip(),
            ','.join(list(set(qos))),
        ))

        self.slurm_out.write("Parent - '{}'\n".format(slurm_account.value))
        for u in sub.subscriptionuser_set.filter(status__name='Active'):
            self.write_account_user(slurm_account.value, u.user.username)

    def handle(self, *args, **options):
        verbosity = int(options['verbosity'])
        root_logger = logging.getLogger('')
        if verbosity > 1:
            root_logger.setLevel(logging.DEBUG)

        self.slurm_out = self.stdout
        if options['output']:
            logger.debug("Writing output to file: {}".format(options['output']))
            self.slurm_out = open(options['output'], 'w')
        else:
            logger.debug("Writing to stdout")

        # Fetch all resources that have a 'Slurm cluster name' attrbiute
        resources = Resource.objects.filter(
                is_available=True,
                resourceattribute__resource_attribute_type__name='Slurm cluster name'
            )

        for r in resources:
            cluster = r.resourceattribute_set.filter(resource_attribute_type__name='Slurm cluster name').first()
            res_qos = r.resourceattribute_set.filter(resource_attribute_type__name='Slurm QOS').first()
            qos = []
            if res_qos is not None:
                qos += res_qos.value.split(',')

            self.write_resource(cluster.value, qos)
            subs = r.subscription_set.prefetch_related(
                    'project',
                    'subscriptionattribute_set',
                    'subscriptionuser_set'
                ).filter(
                    status__name='Active'
                )

            for s in subs:
                self.write_account_from_subscription(r, s)
