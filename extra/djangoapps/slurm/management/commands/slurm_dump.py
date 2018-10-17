import logging
import os

from django.core.management.base import BaseCommand, CommandError

from core.djangoapps.resources.models import ResourceAttribute
from extra.djangoapps.slurm.utils import SLURM_CLUSTER_ATTRIBUTE_NAME
from extra.djangoapps.slurm.associations import SlurmCluster

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Dump slurm assocations for sacctmgr in flat file format'

    def add_arguments(self, parser):
        parser.add_argument("-o", "--output", help="Path to output directory")

    def handle(self, *args, **options):
        self.slurm_out = os.getcwd()
        if options['output']:
            self.slurm_out = options['output']

        if not os.path.isdir(self.slurm_out):
            os.mkdir(self.slurm_out, 0o0700)

        logger.warn("Writing output to directory: %s", self.slurm_out)

        for attr in ResourceAttribute.objects.filter(resource_attribute_type__name=SLURM_CLUSTER_ATTRIBUTE_NAME):
            cluster = SlurmCluster.new_from_resource(attr.resource)
            with open(os.path.join(self.slurm_out, '{}.cfg'.format(cluster.name)), 'w') as fh:
                cluster.write(fh)
