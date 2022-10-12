import os
import sys

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist

from coldfront.core.organization.models import OrganizationLevel, Organization


class Command(BaseCommand):
    help = 'Lists Organizations'

    def add_arguments(self, parser):
        parser.add_argument('--orglevel', '--level',
                help='This flag takes an OrganizationLevel name as its '
                    'argument.  If given, only Organizations at that level '
                    'will be displayed.  You can repeat this argument to '
                    'display for multiple OrgLevels.  By default, all '
                    'organizations are displayed.',
                action='append',
                default=None,
                )
        return


    def handle(self, *args, **options):

        verbosity = options['verbosity']
        olevnames = options['orglevel']
        if olevnames is None:
            olevs = OrganizationLevel.generate_orglevel_hierarchy_list()
        else:
            olevs = []
            for olname in olevnames:
                olev = OrganizationLevel.objects.get(name=olname)
                olevs.append(olev)

        # Now print Orgs by OrgLevel
        for olev in olevs:
            orgs = Organization.objects.filter(organization_level=olev)
            for org in orgs:
                if verbosity == 0:
                    sys.stdout.write('{}\n'.format(org.fullcode()))
                elif verbosity == 1:
                    sys.stdout.write('{}:({}, "{}")\n'.format(
                        org.fullcode(),
                        org.semifullcode(),
                        org.longname
                        ))
                else:
                    sys.stdout.write('{}:({}, "{}")\n'.format(
                        org.fullcode(),
                        org.semifullcode(),
                        org.longname
                        ))
        return
