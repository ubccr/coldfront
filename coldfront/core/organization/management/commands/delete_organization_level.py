import os
import sys

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from coldfront.core.organization.models import (
            OrganizationLevel,
            Organization,
        )


class Command(BaseCommand):
    help = """Deletes an OrganizationLevel
`
    This will delete an OrganizationLevel from the database.

    
    """
    def add_arguments(self, parser):
        parser.add_argument('--name',
                help='The name of the OrganizationLevel to delete',
                action='store',
                required=True,
                )
        parser.add_argument('--force',
                help='Force mode.  Skip DAconfirmation prompt',
                action='store_true',
                )
        return

    def yorn(self, question, default="no"):
        """Prompt for yes or no answer.

        Based on http://code.activestate.com/recipes/577058/
        """
        valid = { 'yes': True, 'y': True, 'ye': True, 'no': False, 'n': False }
        if default is not None:
            default = default.lower()
        prompt = '[y/n]'
        if default == 'yes':
            prompt = '[Y/n]'
        elif default == 'no':
            prompt = '[y/N]'
        else:
            raise ValueError('Invalid value "{}" for default; expecting "yes" or "now"'.format(
                default))

        while True:
            sys.stdout.write('{} {}? '.format(question, prompt))
            choice = input().lower()
            if default is not None and choice == '':
                return valid[default]
            elif choice in valid:
                return valid[choice]
            else:
                sys.stdout.write("Please respond with 'yes' or 'now'")
        #end: while True
    #end: def yorn

    def handle(self, *args, **options):

        name = options['name']
        force = options['force']

        orglev = OrganizationLevel.objects.get(name=name)

        if not force:
            sys.stdout.write('You have requested to delete OrganizationLevel '
                    'name={} (level={})\n'.format(orglev.name, orglev.level))
            orgs = Organization.objects.filter(organization_level=orglev)
            if orgs:
                sys.stdout.write('This will cause the deletion of Organizations:\n')
                for org in orgs:
                    sys.stdout.write('    {}\n'.format(org.fullcode()))

            sys.stdout.write('Although we will try to repair any holes this '
                    'would create in the Organization hierarchy, please be advised '
                    'that this is a serious and tricky operation.')
            yorn = self.yorn('Do you really want to continue', default='no')
            if not yorn:
                sys.stdout.write('Aborting at user request.\n')
                return
        #end: if not force

        orglev.delete_organization_level()
        sys.stderr.write('Deleted organization level {}\n'.format(name))
