import os
import sys

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from coldfront.core.organization.models import (
            OrganizationLevel,
            Organization,
        )


class Command(BaseCommand):
    help = """Deletes an Organization
`
    This will delete an organization with the specified fullcode from the 
    database.

    If --dissociate-users is given, if any Users are associated with the
    Organization being deleted, those associations will be broken.  It it
    is not given, an exception will be raised if any Users are associated
    with the Organization being deleted.

    Similarly, if --dissociate-projects is given, if any Projects are associated
    with the Organization being deleted, those associated will be broken.
    Again, an error will occur if such Projects exist and --dissociate-projects
    was not given.

    --dissociate is a shortcut for specifying both --dissociate-users and 
    --dissociate-projects.

    A fatal error will arise if the Organization being deleted is a parent of
    another Organization.
    """

    def add_arguments(self, parser):
        parser.add_argument('--code',
                help='The fullcode or semifullcode for the Organization to '
                    'delete',
                action='store',
                required=True,
                )
        parser.add_argument('--dissociate_users','--dissociate-users',
                help='Any associations between the Organization and '
                    'users will be deleted.',
                action='store_true',
                )
        parser.add_argument('--dissociate_projects','--dissociate-projects',
                    '--dissociate_projs', '--dissociate-projs',
                help='Any associations between the Organization and '
                    'projects will be deleted.',
                action='store_true',
                )
        parser.add_argument('--dissociate',
                help='Short for --dissociate_projects and --dissociate_users',
                action='store_true',
                )
        return


    def handle(self, *args, **options):

        code = options['code']
        diss_users = options['dissociate_users']
        diss_projs = options['dissociate_projects']
        diss = options['dissociate']

        org = Organization.get_organization_by_fullcode(code)
        if org is None:
            parent = Organization.get_organization_by_semifullcode(
                        code)
        if org is None:
            sys.stderr.write('No Organization {} found, nothing '
                    'to do\n'.format(code))

        if diss:
            diss_users = True
            diss_projs = True

        # Check for child Organizations
        qset = Organization.objects.filter(parent=org)
        if qset:
            children = list(qset.all())
            ccodes = []
            for child in children:
                ccodes.append(child.fullcode())
            cstr = ', '.join(ccodes)
            raise CommandError('Organization {} has children ['
                    '{}], cannot delete'.format(
                        org.fullcode(), cstr))
        #end: if qset

        # Check for projects associated with Organization
        qset = OrganizationProject.objects.filter(organization=org)
        if qset:
                if diss_projs:
                    # Disassociate Org from all projects
                    qset.delete()
                else:
                    # Error
                    plist = []
                    for tmp in qset:
                        plist.append(tmp.title)
                    raise CommandError('Organization {} is referred '
                            'to by projects [{}], cannot delete.\n'.format(
                                org.fullcode(), ', '.join(plist)))
                #end: if diss_projs
        #end: if qset

        # Check for users associated with Organization
        qset = OrganizationUser.objects.filter(organization=org)
        if qset:
                if diss_users:
                    # Disassociate Org from all users
                    qset.delete()
                else:
                    # Error
                    ulist = []
                    for tmp in qset:
                        ulist.append(tmp.user.user.username)
                    raise CommandError('Organization {} is referred '
                            'to by users [{}], cannot delete.\n'.format(
                                org.fullcode(), ', '.join(ulist)))
                #end: if diss_users
        #end: if qset

        fcode = org.fullcode()
        org.delete()
        sys.stderr.write('Deleted organization {}\n'.format(fcode))
