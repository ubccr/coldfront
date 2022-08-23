import os
import logging

from coldfront.core.resource.models import ResourceAttribute
from coldfront.plugins.slurm.utils import SLURM_CLUSTER_ATTRIBUTE_NAME, SLURM_DUMP_TASK_BASE_DIR
from coldfront.plugins.slurm.associations import SlurmCluster

logger = logging.getLogger(__name__)


def run_slurm_dump():
    base_dir = SLURM_DUMP_TASK_BASE_DIR
    if not base_dir:
        base_dir = os.getcwd()

    for attr in ResourceAttribute.objects.filter(resource_attribute_type__name=SLURM_CLUSTER_ATTRIBUTE_NAME):
        if not attr.resource.is_available:
            continue

        cluster = SlurmCluster.new_from_resource(attr.resource)

        out_dir = os.path.join(base_dir, attr.resource.name.lower())
        if not os.path.isdir(out_dir):
            os.mkdir(out_dir, 0o0700)

        with open(os.path.join(out_dir, '{}.cfg'.format(cluster.name)), 'w') as fh:
            cluster.write(fh)

        logger.info('Created slurm flat file for {}'.format(cluster.name))
