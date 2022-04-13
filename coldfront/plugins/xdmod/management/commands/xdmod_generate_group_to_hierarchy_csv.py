import logging
import os

from django.core.management.base import BaseCommand, CommandError

from coldfront.plugins.xdmod.utils import (
        generate_xdmod_group_to_hierarchy
    )
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """Generate an XdMod group-to-hierarchy.csv file from ColdFront Organization hierarchy.

            This finds all ColdFront Allocations with an attribute of name
            given by SLURM_ACCOUNT_ATTRIBUTE_NAME setting, and will make an
            entry in the group-to-hierarchy.csv file according to the values
            of other configuration settings (e.g. XDMOD_ALLOCATION_IN_HIERARCHY,
            XDMOD_PROJECT_IN_HIERARCHY, XDMOD_ALLOCATION_HIERARCHY_CODE* and
            XDMOD_PROJECT_HIERARCHY_CODE*)
        """

    def add_arguments(self, parser):
        parser.add_argument('--output_file', '--outfile', '--file', '--out',
                            help='Name/path of output file',
                            action='store',
                            default='group-to-hierarchy.csv',
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

        outdata = generate_xdmod_group_to_hierarchy()
        with open(outfile, 'w') as fh:
            for outrec in outdata:
                code = outrec[0]
                name = outrec[1]
                if code is None:
                    code = ''
                if name is None:
                    name = ''
                fh.write('"{}","{}"\n'.format(code, name))
