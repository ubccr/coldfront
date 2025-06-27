import logging
import csv
import os

from django.core.management.base import BaseCommand
from coldfront.core.allocation.models import Allocation
from coldfront.core.school.models import School

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Dump allocation association hierarchy for use by XDMoD"

    def add_arguments(self, parser):
        parser.add_argument("-o", "--output", help="Path to output directory")
        parser.add_argument(
            "-c", "--cluster", help="Only output specific Slurm cluster"
        )

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
            root_logger.setLevel(logging.WARN)

        out_dir = None
        if options["output"]:
            out_dir = options["output"]
            if not os.path.isdir(out_dir):
                os.mkdir(out_dir, 0o0700)

            logger.info(
                f"Writing XDMoD hierarchy mapping files \
                to directory:{out_dir}"
            )

        all_schools = School.objects.all()
        all_allocations = Allocation.objects.all()

        with open(os.path.join(out_dir, "hierarchy.csv"), "w") as csvfile:
            hierarchy_writer = csv.writer(
                csvfile,
                delimiter=",",
                dialect="unix",
                quotechar='"',
                quoting=csv.QUOTE_ALL,
            )

            # the only unit we use (top level)
            logging.info("Writing top level unit")
            hierarchy_writer.writerow(["NYU", "NYU", ""])

            # each shool is a division (middle level)
            logging.info("Writing schools as middle level units")
            for school in all_schools:
                hierarchy_writer.writerow(
                    [school.description, school.description, "NYU"]
                )

            # each allocation is a department (bottom level)
            logging.info("Writing allocations as bottom level units")
            for allocation in all_allocations:
                hierarchy_writer.writerow(
                    [
                        allocation.get_attribute("slurm_account_name"),
                        allocation.get_attribute("slurm_account_name"),
                        allocation.project.school.description,
                    ]
                )

        with open(os.path.join(out_dir, "group-to-hierarchy.csv"), "w") as csvfile:
            hierarchy_writer = csv.writer(
                csvfile,
                delimiter=",",
                dialect="unix",
                quotechar='"',
                quoting=csv.QUOTE_ALL,
            )

            logging.info("Writing allocations as groups to map to themselves")
            # each allocation is a department (bottom level)
            for allocation in all_allocations:
                hierarchy_writer.writerow(
                    [
                        allocation.get_attribute("slurm_account_name"),
                        allocation.get_attribute("slurm_account_name"),
                    ]
                )
