import os
import sys

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from coldfront.core.organization.models import (
            OrganizationLevel,
        )


class Command(BaseCommand):
    help = """Adds an OrganizationLevel.

    It is recommended to rename existing OrganizationLevels rather than
    inserting/deleting if possible.

    However, if you need to insert, this should insert an OrganizationLevel
    and placeholder Organizations.
    """

    def add_arguments(self, parser):
        def_delimiter = '|'

        parser.add_argument('-name',
                help='The name of the OrganizationLevel to add.',
                action='store',
                )
        parser.add_argument('-level',
                help='The integer level of the OrganizationLevel to add.',
                action='store',
                )
        parser.add_argument('-parent',
                help='The name of the parent OrganizationLevel.',
                action='store',
                default=None,
                )
        parser.add_argument('-export_to_xdmod', '-export-to-xdmod', '--export',
                help='Whether OrganizationLevel should export to xdmod',
                action='store_true',
                )
        return


    def handle(self, *args, **options):

        name = options['name']
        level = options['level']
        pname = options['parent']
        export = options['export_to_xdmod']

        if pname is None:
            parent = None
        else:
            parent = OrganizationLevel.objects.get(name=name)
        
        new = OrganizationLevel.add_organization_level(
                name=name,
                level=level,
                export_to_xdmod=export,
                parent=parent,
            )
        sys.stderr.write('Created new organization level.\n')
