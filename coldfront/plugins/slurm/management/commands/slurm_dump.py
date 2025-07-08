# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import os

from django.core.management.base import BaseCommand

from coldfront.core.resource.models import ResourceAttribute
from coldfront.plugins.slurm.associations import SlurmCluster
from coldfront.plugins.slurm.utils import SLURM_CLUSTER_ATTRIBUTE_NAME

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Dump slurm associations for sacctmgr in flat file format"

    def add_arguments(self, parser):
        parser.add_argument("-o", "--output", help="Path to output directory")
        parser.add_argument("-c", "--cluster", help="Only output specific Slurm cluster")

    def handle(self, *args, **options):
        verbosity = int(options["verbosity"])
        root_logger = logging.getLogger("")
        if verbosity == 0:
            root_logger.setLevel(logging.ERROR)
        elif verbosity == 2:
            root_logger.setLevel(logging.INFO)
        elif verbosity == 3:
            root_logger.setLevel(logging.DEBUG)
        else:
            root_logger.setLevel(logging.WARNING)

        out_dir = None
        if options["output"]:
            out_dir = options["output"]
            if not os.path.isdir(out_dir):
                os.mkdir(out_dir, 0o0700)

            logger.warning("Writing output to directory: %s", out_dir)

        for attr in ResourceAttribute.objects.filter(resource_attribute_type__name=SLURM_CLUSTER_ATTRIBUTE_NAME):
            if options["cluster"] and options["cluster"] != attr.value:
                continue

            if not attr.resource.is_available:
                continue

            cluster = SlurmCluster.new_from_resource(attr.resource)
            if not out_dir:
                cluster.write(self.stdout)
                continue

            with open(os.path.join(out_dir, "{}.cfg".format(cluster.name)), "w") as fh:
                cluster.write(fh)
