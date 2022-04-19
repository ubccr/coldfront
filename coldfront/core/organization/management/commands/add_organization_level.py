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

    If parent is not specified, this will attempt to create a new "root"
    OrganizationLevel, in which case the level must be greater than any 
    existing OrganizationLevel, and any Organizations at the previous root
    level will be made children of a new 'Unknown' placeholder Organization
    at the new root level.

    In other cases, parent should be the name of an OrganizationLevel to be
    the parent of the new OrganizationLevel. In this case, new OrganizationLevel
    will be placed beneath that parent, but above any existing child of that
    parent, and the level must be strictly less than the level of the parent, 
    and greater than the level of the child of that parent (if the parent has 
    a child). If the parent has an existing child OrganizationLevel, than for
    every Organization at the child OrganizationLevel, a placeholder Organization
    at the new OrganizationLevel will be created and that will become the new
    parent of the Organization at that level.

    However, if you need to insert, this should insert an OrganizationLevel
    and placeholder Organizations.
    """

    def add_arguments(self, parser):
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
