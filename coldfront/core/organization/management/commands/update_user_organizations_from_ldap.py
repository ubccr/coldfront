import os
import sys

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist

from coldfront.core.utils.common import import_from_settings
from coldfront.core.organization.models import Organization
from coldfront.core.user.models import UserProfile
from coldfront.plugins.ldap_user_search.utils import LDAPUserSearch

ORGANIZATION_LDAP_USER_ATTRIBUTE = import_from_settings(
        'ORGANIZATION_LDAP_USER_ATTRIBUTE', None)


class Command(BaseCommand):
    help = 'Updates Organizations for user from LDAP'

    def add_arguments(self, parser):
        def_delimiter = '|'

        parser.add_argument('-u', '--user',
                help='Username of user whose Organizations should be updated '
                    'from LDAP.  Repeat for multiple users. Incompatible with'
                    '--all',
                action='append',
                default=[],
                )
        parser.add_argument('--all',
                help='Update Organizations for all (active) User objects.  '
                    'Incompatible with --user.',
                action='store_true',)
        parser.add_argument('-p', '--parents', '--add-parents',
                action='store_true',
                help='If set, we will also add any and all ancestors of '
                    'Organizations obtained from LDAP.', 
                    )
        parser.add_argument('-d', '--delete',
                action='store_true',
                help='If set, we will also delete any Organizations the user '
                    'currently belongs to if not present in the list from '
                    'LDAP (after adding ancestors if so requested)'
                    )
        parser.add_argument('--create-placeholder', '--create', '--placeholder',
                action='store_true',
                help='If set, if an LDAP directory_string found which we '
                    'cannot convert to an Organization is encountered, '
                    'will create a placeholder Organization and assign '
                    'it to user',
                    )
        parser.add_argument('--dryrun',
                action='store_true',
                help='If set, we will do the LDAP search but print results '
                    'rather than applying them.  Implies verbosity >= 1.'
                    )
        return


    def handle(self, *args, **options):

        users = options['user']
        allusers = options['all']
        addparents = options['parents']
        delete = options['delete']
        dryrun = options['dryrun']
        verbosity = options['verbosity']
        create_placeholder = options['create-placeholder']

        v_or_d_text = '[VERBOSE]'
        if dryrun:
            v_or_d_text = '[DRYRUN]'
            if not verbosity:
                verbosity=1

        if allusers:
            if users and len(list(users)) > 0:
                raise CommandError('The options --all and --user are '
                        'mutally exclusive')
            users = UserProfile.objects.filter(user__is_active=True)
        else:
            if users and len(list(users)) > 0:
                tmp = UserProfile.objects.filter(user__username__in=users)
                users = tmp
            else:
                raise CommandError('You must provide either the --all or the '
                    '--user flag (but not both)')

        for userprof in users:
            ldap = LDAPUserSearch(
                    user_search_string=userprof.user.username,
                    search_by='username_only')
            results = ldap.search_a_user(
                    user_search_string=userprof.user.username,
                    search_by='username_only')
            if results:
                userrec = results[0]
                directory_strings = []
                if 'directory_strings' in userrec:
                    directory_strings = userrec['directory_strings']
                results= Organization.update_user_organizations_from_dirstrings(
                        user=userprof,
                        dirstrings = directory_strings,
                        addParents = addparents,
                        dryrun = dryrun,
                        delete = delete,
                        createUndefined = create_placeholder,
                        )
                if verbosity:
                    username = userprof.user.username
                    orgs = results['added']
                    for org in orgs:
                        sys.stdout.write('{} Added org {} to user '
                            '{}\n'.format(
                            v_or_d_text, 
                            org.fullcode(),
                            username))
                    orgs = results['removed']
                    for org in orgs:
                        sys.stdout.write('{} Removed org {} from user '
                            '{}\n'.format(
                            v_or_d_text, 
                            org.fullcode(),
                            username))
            else:
                if verbosity:
                    username = userprof.user.username
                    sys.stdout.write('[{}] Unable to get organizations for {} '
                            'from LDAP'.format(v_or_d_text, username))
        return
