import logging
import os

from django.core.management.base import BaseCommand, CommandError

from coldfront.plugins.xdmod.utils import (
        generate_xdmod_names_for_users,
    )
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """Generate an XdMod names.csv file from ColdFront Users.

            This will create a list correlating the user, first and last 
            names for each User with an username in Coldfront.

            The output will depend on the values of the
            XDMOD_NAMES_CSV_USER_FNAME_FORMAT and XDMOD_NAMES_CSV_USER_LNAME_FORMAT
            configuration variables.
        """

    def add_arguments(self, parser):
        parser.add_argument('--output_file', '--outfile', '--file', '--out',
                            help='Name/path of output file',
                            action='store',
                            default='names.csv',
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

        outdata = []
        tmp = generate_xdmod_names_for_users()
        outdata.extend(tmp)

        with open(outfile, 'w') as fh:
            for outrec in outdata:
                uname = outrec[0]
                fname = outrec[1]
                lname = outrec[2]
                if uname is None:
                    uname = ''
                if fname is None:
                    fname = ''
                if lname is None:
                    lname = ''
                fh.write('"{}","{}","{}"\n'.format(uname, fname, lname))

