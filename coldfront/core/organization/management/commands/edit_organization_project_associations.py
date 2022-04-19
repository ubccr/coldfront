import os
import sys

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from coldfront.core.organization.models import (
            OrganizationLevel,
            OrganizationProject,
            Organization,
        )
from coldfront.core.project.models import (
            Project,
        )

class Command(BaseCommand):
    help = """Associates/disassociates Organizations and Projects.

    This script can edit Organization-Project associations.

    Projects can be specified by title.
    Organizations can be specified by fullcode or semifullcode.
    
    Mode can be one of:
        * 'add': Add Organizations as secondary Organizations for
            the specified project.
        * 'delete': Delete Organizations from the specified project.
        * 'primary': Make the specified Organization primary (adding
            it if needed)

    Multiple organizations can be specified; however for mode 'primary'
    only the first Organization specified will be made primary (the
    remainder will be added as secondary orgs, i.e."add")
    """

    def add_arguments(self, parser):
        parser.add_argument('--organization', '--org',
                help='The code for the Organization to associate/dissociate',
                action='append',
                default=[],
                )
        parser.add_argument('--project','--proj',
                help='The title of the project',
                action='store',
                required=True,
                )
        parser.add_argument('--mode',
                help='The operational mode.  It can be "add", or '
                    '"delete" or "primary"',
                action='store',
                required=True,
                )
        return


    def handle(self, *args, **options):

        verbosity = options['verbosity']

        title = options['project']
        proj = Project.objects.get(title=title)

        mode = options['mode']
        if mode == 'add':
            pass
        elif mode == 'delete' or mode == 'del':
            mode = 'delete'
        elif mode == 'primary':
            pass
        else:
            raise CommandError('Invalid value {} for mode; expecting one '
                    'of "add", "delete", or "primary".'.format(mode))

        orgs = options['organization']
        for ocode in orgs:
            org = Organization.get_organization_by_fullcode(ocode)
            if org is None:
                org = Organization.get_organization_by_semifullcode(ocode)
            if org is None:
                raise CommandError('No Organization for {} found.\n'.format(
                    ocode))

            if mode == 'primary':
                mode = 'add'
                oldprim, _ = OrganizationProject.set_primary_organization_for_project( 
                    proj, org)

                if oldprim == org:
                    if verbosity > 1:
                        sys.stderr.write('Organization {} is already primary '
                            'organization for project "{}"\n'.format(
                                org.fullcode(), title))
                else:
                    if verbosity:
                        sys.stderr.write('Organization {} made primary '
                            'organization for project "{}", replacing '
                            '{}\n'.format(
                                org.fullcode(), title, oldprim.fullcode()))
                #end: if oldprim
            elif mode == 'add':
                new, created, changes = \
                        OrganizationProject.get_or_create_or_update_organization_project(
                            org, proj, is_primary=False)
                if created:
                    if verbosity:
                        sys.stderr.write('Organization {} added to project '
                            '"{}"\n'.format(org.fullcode(), title))
                #end: if created
            elif mode == 'delete':
                qset = OrganizationProject.objects.filter(
                    organization=org, project=proj)
                if qset:
                    obj = qset[0]
                    obj.delete()
                    if verbosity:
                        sys.stderr.write('Organization {} disassociated with '
                            'project "{}"\n'.format(
                                org.fullcode(), title))
                else:
                    if verbosity > 1:
                        sys.stderr.write('Organization {} not associated '
                            'with project "{}", nothing to disassociate.\n'.format(
                                org.fullcode(), title))
                #end: if qset
            else:
                raise CommandError('Illegal mode {}'.format(mode))
            #end: if mode == 'primary'
        #end: for ocode in orgs:
