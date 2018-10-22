import logging
import os

from django.core.management.base import BaseCommand, CommandError

from coldfront.core.resources.models import ResourceAttribute
from coldfront.plugins.slurm.utils import SLURM_CLUSTER_ATTRIBUTE_NAME
from coldfront.plugins.slurm.associations import SlurmCluster

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Dump slurm assocations for sacctmgr in flat file format'

    def add_arguments(self, parser):
        parser.add_argument("-o", "--output", help="Path to output directory")
        parser.add_argument("-c", "--cluster", help="Only output specific Slurm cluster")

    def handle(self, *args, **options):
        out_dir = None
        if options['output']:
            out_dir = options['output']
            if not os.path.isdir(out_dir):
                os.mkdir(out_dir, 0o0700)

            logger.warn("Writing output to directory: %s", out_dir)

        for attr in ResourceAttribute.objects.filter(resource_attribute_type__name=SLURM_CLUSTER_ATTRIBUTE_NAME):
            if options['cluster'] and options['cluster'] != attr.value:
                continue

            cluster = SlurmCluster.new_from_resource(attr.resource)
            if not out_dir:
                cluster.write(self.stdout)
                continue

            with open(os.path.join(out_dir, '{}.cfg'.format(cluster.name)), 'w') as fh:
                cluster.write(fh)
