import os
import sys

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from coldfront.core.organization.models import (
            OrganizationLevel,
            Organization,
        )


class Command(BaseCommand):
    help = """Adds an Organization

    This will add an organization to the database.
    Longname and shortname will default to the other, or if neither
    given to code.

    level can be the fullcode or semifullcode of an OrganizationLevel.
    """

    def add_arguments(self, parser):
        parser.add_argument('--code',
                help='The code for the Organization to create',
                action='store',
                required=True,
                )
        parser.add_argument('--shortname','--short',
                help='The shortname of the Organization to create',
                action='store',
                default=None,
                )
        parser.add_argument('--longname','--long',
                help='The longname of the Organization to create',
                action='store',
                default=None,
                )
        parser.add_argument('--organization_level', '--organization-level',
                '--level',
                help='The name of the OrganizationLevel for this Organization',
                action='store',
                required=True,
                )
        parser.add_argument('--parent',
                help="The fullcode of the new Organizaton's parent, if any",
                action='store',
                default=None,
                )
        parser.add_argument('--is_selectable_for_user', '--user_selectable',
                '--user',
                help='Whether Organization should be selectable by user',
                action='store_true',
                )
        parser.add_argument('--is_selectable_for_project', '--project_selectable',
                '--project', '--proj',
                help='Whether Organization should be selectable by project',
                action='store_true',
                )
        parser.add_argument('--selectable', '--is_selectable',
                help='Short for --is_selectable_for_user and --is_selectable_for_project',
                action='store_true',
                )
        return


    def handle(self, *args, **options):

        code = options['code']
        shortname = options['shortname']
        longname = options['longname']
        selectable = options['selectable']
        user_selectable = options['is_selectable_for_user']
        proj_selectable = options['is_selectable_for_project']
        pcode = options['parent']
        orglev_name = options['organization_level']
        
        if shortname is None:
            if longname is None:
                shortname = code
                longname = code
            else:
                shortname = longname
        elif longname is None:
            longname = shortname

        if pcode is None:
            parent = None
        else:
            parent = Organization.get_organization_by_fullcode(pcode)
            if parent is None:
                parent = Organization.get_organization_by_semifullcode(
                        pcode)
            if parent is None:
                raise CommandError('Unable to convert {} to a parent '
                        'Organization'.format(pcode))

        if orglev_name is None:
                raise CommandError('No organization_level specified')
        olev = OrganizationLevel.objects.get(name=orglev_name)

        if selectable:
            user_selectable = True
            proj_selectable = True

        new, created, changes = Organization.create_or_update_organization_by_parent_code(
                code=code,
                parent=parent,
                organization_level=olev,
                shortname=shortname,
                longname=longname,
                is_selectable_for_user=user_selectable,
                is_selectable_for_project=proj_selectable,
            )

        if created:
            sys.stderr.write('Created new organization {}\n'.format(
                new.fullcode()))
        elif changes:
            sys.stderr.write('Existing organization {} modified\n'.format(
                new.fullcode()))
            for key, val in changes.items():
                old = val['old']
                new = val['new']
                sys.stderr.write('    {} changed from {} to {}\n'.format(
                    key, old, new))
            #end: for key, val
        else:
            sys.stderr.write('No changes to organization {}\n'.format(
                new.fullcode()))
        #end: if created
