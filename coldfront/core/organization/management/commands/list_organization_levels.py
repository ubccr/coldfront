import os
import sys

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist

from coldfront.core.organization.models import OrganizationLevel


class Command(BaseCommand):
    help = 'Lists OrganizationLevels'

#    def add_arguments(self, parser):
#        parser.add_argument('--status', '-s',
#                help='By default, all matching projects are displayed.  If '
#                    'a status is given, only matching projects with a matching '
#                    'status are displayed.  This can be repeated to allow '
#                    'matching multiple statuses',
#                action='append',
#                default=[],
#                )
#        return


    def handle(self, *args, **options):

        ordering = '-level'
        verbosity = options['verbosity']

        olevs = OrganizationLevel.objects.all().order_by(ordering)
        for olev in olevs:
            if verbosity == 0:
                sys.stdout.write('{}\n'.format(olev.name))
            elif verbosity == 1:
                sys.stdout.write('{}:{}\n'.format(olev.name, olev.level))
            else:
                pname = ''
                if olev.parent is not None:
                    pname = olev.parent.name
                sys.stdout.write('{}:{}:Parent={}:xport2xdmod={}\n'.format(
                    olev.name, olev.level, pname, olev.export_to_xdmod))
        return
