import os
import sys

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist

from coldfront.core.utils.common import import_from_settings
from coldfront.core.organization.models import Directory2Organization
from coldfront.core.user.models import UserProfile
from coldfront.plugins.ldap_user_search.utils import LDAPUserSearch


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
        parser.add_argument('-d', '--delete',
                action='store_true',
                help='If set, we will also delete any Organizations the user '
                    'currently belongs to if not present in the list from '
                    'LDAP (after adding ancestors if so requested)'
                    )
        parser.add_argument('--create_placeholder', 
                '--create-placeholder', '--create', '--placeholder',
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
        delete = options['delete']
        dryrun = options['dryrun']
        verbosity = options['verbosity']
        create_placeholder = options['create_placeholder']

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
            username = userprof.user.username
            ldap = LDAPUserSearch(
                    user_search_string=username,
                    search_by='username_only')
            results = ldap.search_a_user(
                    user_search_string=username,
                    search_by='username_only')
            ldapstrings = []
            firstIsPrimary = False
            if results:
                userrec = results[0]
                if 'primary_organization' in userrec:
                    tmp = userrec['primary_organization']
                    if tmp:
                        ldapstrings = [tmp]
                        firstIsPrimary = True
                if 'organizations' in userrec:
                    tmp = userrec['organizations']
                    if tmp:
                        ldapstrings.extend(tmp)
            else: # if results
                if verbosity:
                    sys.stderr.write('No results found for LDAP lookup of {}\n'.format(
                        username))
                    continue
            #end: if results

            if dryrun:
                primary = None
                secondary = []
                if firstIsPrimary:
                    tmp = Directory2Organization.convert_strings_to_orgs(
                            [ldapstrings[0]], createUndefined=False)
                    if tmp:
                        primary = tmp
                    ldapstrings = ldapstrings[1:]
                secondary = Directory2Organization.convert_strings_to_orgs(
                        ldapstrings, createUndefined=False)

                sys.stderr.write('[DRYRUN] Organizations for user {} are\n'.format(
                    username))
                printed = set()
                if primary:
                    primary = primary[0]
                    fcode = primary.fullcode()
                    sys.stderr.write('[DRYRUN]    {} (primary)\n'.format(
                        fcode))
                    printed.add(fcode)
                for tmp in secondary:
                    fcode = tmp.fullcode()
                    if fcode in printed:
                        pass
                    else:
                        sys.stderr.write('[DRYRUN]    {}\n'.format(
                            fcode))
                        printed.add(fcode)
                #end: for tmp in secondary
                # and skip to next user
                continue
            else: #if dryrun
                results= Directory2Organization.update_user_organizations_from_ldapstrings(
                        user=userprof,
                        ldapstrings = ldapstrings,
                        firstIsPrimary = firstIsPrimary,
                        delete = delete,
                        createUndefined = create_placeholder,
                        )
                if verbosity:
                    username = userprof.user.username
                    for fcode, rec in results.items():
                        if fcode is None:
                            continue
                        old = None
                        new = None
                        if 'old' in rec:
                            old = rec['old']
                        if 'new' in rec:
                            new = rec['new']
                        if old is None:
                            if new is None:
                                # Both old and new are None, nothing to report
                                continue
                            elif new is 'primary':
                                sys.stdout.write('{} Added Org {} as primary for user {}\n'.format(
                                    v_or_d_text, fcode, username))
                            else:
                                sys.stdout.write('{} Added Org {} as secondary for user {}\n'.format(
                                    v_or_d_text, fcode, username))
                            #end: if new is None
                        elif old is 'primary':
                            if new is None:
                                sys.stdout.write('{} Deleted former primary Org {} from user {}\n'.format(
                                    v_or_d_text, fcode, username))
                            elif new is 'primary':
                                # Both old and new are primary, nothing to report
                                continue
                            else:
                                sys.stdout.write('{} Demoted Org {} from primary to secondary for user {}\n'.format(
                                    v_or_d_text, fcode, username))
                            #end: if new is None

                        else:
                            if new is None:
                                sys.stdout.write('{} Deleted former secondary Org {} from user {}\n'.format(
                                    v_or_d_text, fcode, username))
                            elif new is 'primary':
                                sys.stdout.write('{} Promoted Org {} from secondary to primary for user {}\n'.format(
                                    v_or_d_text, fcode, username))
                            else:
                                # Both old and new are secondary, nothing to report
                                continue
                            #end: if new is None
                        #end: if old is None
                    #end: for fcode, rec in results.items()
            #end: if dryrun
        return
