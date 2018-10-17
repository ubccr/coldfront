import logging
import os
import sys

from django.core.management.base import BaseCommand, CommandError

from core.djangoapps.resources.models import ResourceAttribute
from extra.djangoapps.slurm.associations import SlurmCluster
from extra.djangoapps.slurm.utils import slurm_check_assoc, slurm_remove_assoc, \
              slurm_add_assoc, SLURM_CLUSTER_ATTRIBUTE_NAME, \
              SLURM_ACCOUNT_ATTRIBUTE_NAME, SLURM_USER_SPECS_ATTRIBUTE_NAME

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Check for Slurm associations that should be removed'

    def add_arguments(self, parser):
        parser.add_argument("-i", "--input", help="Input sacctmgr dump flat file", required=True)
        parser.add_argument("-s", "--sync", help="Sync changes to Slurm", action="store_true")
        parser.add_argument("-u", "--username", help="Check specific username")
        parser.add_argument("-a", "--account", help="Check specific account")

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

        with open(options['input']) as fh:
            slurm_cluster = SlurmCluster.new_from_stream(fh)

        try:
            resource = ResourceAttribute.objects.get(resource_attribute_type__name=SLURM_CLUSTER_ATTRIBUTE_NAME, value=slurm_cluster.name).resource
        except ResourceAttribute.DoesNotExist:
            logger.error("No Slurm '%s' cluster resource found in Coldfront using '%s' attribute", slurm_cluster.name, SLURM_CLUSTER_ATTRIBUTE_NAME)
            sys.exit(1)

        coldfront_cluster = SlurmCluster.new_from_resource(resource)

        for name, account in slurm_cluster.accounts.items():
            if name in coldfront_cluster.accounts:
                remove = []
                for uid in account.users:
                    if uid in coldfront_cluster.accounts[name].users:
                        remove.append(uid)

                for u in remove:
                    slurm_cluster.accounts[name].users.pop(u)

        remove = []
        for name, account in slurm_cluster.accounts.items():
            if len(account.users) == 0:
                remove.append(name)

        for a in remove:
            slurm_cluster.accounts.pop(a)

        slurm_cluster.write(self.stdout)
