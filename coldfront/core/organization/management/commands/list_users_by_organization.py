import os
import sys

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist

from coldfront.core.utils.common import import_from_settings
from coldfront.core.organization.models import Organization
from coldfront.core.user.models import UserProfile


class Command(BaseCommand):
    help = 'Lists users belongs to an Organization'

    def add_arguments(self, parser):
        def_delimiter = '|'

        parser.add_argument('-o', '--organization', '--org',
                help='The fullcode of the Organization being queried. '
                    'Maybe repeated to give multiple Organizations (in which '
                    'case any user found in any of them will be listed, unless '
                    '--and is given.',
                action='append',
                default=[],
                )
        parser.add_argument('--and',
                help='If multiple Organizations are given, only list users '
                    'which are found in all of them.  Default is to list users '
                    'in any of them',
                action='store_true',)
        parser.add_argument('--descendents', '--children', '-c',
                help='If set, then when matching against a given fullcode of '
                    'an Organization, we consider an user to match if the '
                    'user belongs to any Organization descended from the named '
                    'Organization.  If unset (default), an user matches only '
                    'if it belongs to the named Organization.',
                action='store_true',
                )
        parser.add_argument('--inactive', '-i',
                help='Normally, only active users are displayed.  If the '
                    '--inactive flag is given, inactive users will be '
                    'displayed as well.',
                action='store_true',
                )
        return


    def handle(self, *args, **options):

        orgcodes = options['organization']
        andorgs = options['and']
        verbosity = options['verbosity']
        descendents = options['descendents']

        users = set()
        for orgcode in orgcodes:
            org = Organization.get_organization_by_fullcode(orgcode)
            if org is None:
                raise CommandError('No Organization with fullcode {} '
                        'found, aborting'.format(orgcode))
            orgs = [ org ]
            if descendents:
                orgs.extend(org.descendents())

            tmpusers = UserProfile.objects.filter(
                    organizations__in=orgs)

            tmpuset = set(tmpusers.all())
            if andorgs:
                users = users.intersection(tmpuset)
            else:
                users = users.union(tmpuset)

        # Convert to list and output
        users = list(users)
        users = sorted(users, key=lambda x: x.user.last_name)
        for user in users:
            if verbosity:
                status = 'INACTIVE'
                if user.user.is_active:
                    status='Active'

                sys.stdout.write('{uname}: {last}, {first} [{status}]\n'.format(
                    uname=user.user.username, 
                    last=user.user.last_name, 
                    first=user.user.first_name,
                    status=status))
            else:
                sys.stdout.write('{}\n'.format(
                    user.user.username))
        return
