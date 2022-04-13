import os
import sys
import json
from os.path import exists

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from coldfront.core.organization.models import OrganizationLevel

class Command(BaseCommand):
    help = 'Generate hierarchy.json for XdMod from OrganizationLevels'

    def add_arguments(self, parser):
        default_outfile = 'hierarchy.json'

        parser.add_argument('-o', '--output', '--outfile'
                help='Name of output file.  Defaults to {}'.format(
                    default_outfile),
                default=default_outfile,
                )
        parser.add_argument('-FORCE',
                help='If set, will clobber existing outfile',
                action='store_true',
                dest='force',
                )
        return


    def handle(self, *args, **options):

        outfile = options['outfile']
        force = options['force']

        if exists(outfile):
            if not force:
                raise CommandError('Refusing to clobber existing output file '
                        '{} without --FORCE flag'.format(outfile))

        hierarchy = OrganizationLevel.generate_xdmod_orglevel_hierarchy_setup()

        with open(outfile, 'w') as fh:
            json.dump(hierarchy, fh)
        return



        
