import json
import logging
import os

from django.core.management.base import BaseCommand, CommandError

from coldfront.plugins.xdmod.utils import (
        generate_xdmod_orglevel_hierarchy_setup
    )
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """Generate an XdMod hierarchy.json file from ColdFront Organization hierarchy.

            This will create file with a json data structure describing
            the tiers in the XdMod hierarchy, built based on the
            OrganizationLevels in ColdFront.  Output is dependent on
            the XDMOD_ALLOCATION_IN_HIERARCHY, XDMOD_PROJECT_IN_HIERARCHY
            configuration settings.

            *NOTE*:  This code does *not* use XDMOD_MAX_HIERARCHY_TIERS;
            at present time it generates a json data structure which
            is inherently restricted to 3 layers.
        """

    def add_arguments(self, parser):
        parser.add_argument('--output_file', '--outfile', '--file', '--out',
                            help='Name/path of output file',
                            action='store',
                            default='hierarchy.json',
                        )
        parser.add_argument('--force', '--FORCE',
                            help='Enable FORCE mode, which allows us to clobber '
                                'existing files',
                            action='store_true',
                        )

    def handle(self, *args, **options):
        outfile = options['output_file']
        FORCE = options['force']

        if os.path.exists(outfile):
            if FORCE:
                logger.warn('Clobbering existing file {} due to FORCE'.format(
                    outfile))
            else:
                raise CommandError('Refusing to clobber existing outfile '
                        '{} without --force.'.format(outfile))

        outdata = generate_xdmod_orglevel_hierarchy_setup()
        with open(outfile, 'w') as fh:
            json.dump(outdata, fh)

