import os
import sys

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.contrib.auth.models import User

from coldfront.core.organization.models import (
            Organization,
            OrganizationUser,
        )
from coldfront.core.user.models import UserProfile


class Command(BaseCommand):
    help = 'Lists users belongs to an Organization'

    def add_arguments(self, parser):
        parser.add_argument('-o', '--organization', '--org',
                help='The fullcode of the Organization being queried. '
                    'Maybe repeated to give multiple Organizations (in which '
                    'case any user found in any of them will be listed, unless '
                    '--and is given.',
                action='append',
                default=[],
                )
        parser.add_argument('--primary_only', '--primary-only',
                '--primary_organization_only', '--primary_organization',
                '--primary-organization-only', '--primary-organization',
                '--primary_org', '--primary-org',
                '--primaryorg', '--primary',
                help='If set, only consider primary organizations in '
                    'matching users.  Normally we match users if '
                    'either primary or additional_organizations match.',
                action='store_true',)
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
        parser.add_argument('--pis_only', '--pis',
                help='If this flag is given, limit output to users who have '
                    'the "is_pi" flag set',
                action='store_true',
                )
        return


    def handle(self, *args, **options):

        orgcodes = options['organization']
        andorgs = options['and']
        verbosity = options['verbosity']
        descendents = options['descendents']
        primary_only = options['primary_only']
        inactive = options['inactive']
        pis_only = options['pis_only']

        # Generate our filter

        #   status filter
        statusQ = None
        if inactive:
            # Include inactive users, no additional filter
            pass
        else:
            tmpQ = Q(user__user__is_active=True)
            if statusQ is None:
                statusQ = tmpQ
            else:
                statusQ = statusQ & tmpQ
        if pis_only:
            tmpQ = Q(user__is_pi=True)
            if statusQ is None:
                statusQ = tmpQ
            else:
                statusQ = statusQ & tmpQ

        #   organization filter
        orgQ = None
        for orgcode in orgcodes:
            org = Organization.get_organization_by_fullcode(orgcode)
            if org is None:
                raise CommandError('No Organization with fullcode {} '
                        'found, aborting'.format(orgcode))
            orgs = [ org ]
            if descendents:
                orgs.extend(org.descendents())

            orgcodeQ = Q(organization__in=orgs)
            if orgQ is None:
                orgQ = orgcodeQ
            elif andorgs:
                orgQ = orgQ & orgcodeQ
            else:
                orgQ = orgQ | orgcodeQ
            #end: if orgQ is None
        #end: for orgcode
        if orgQ is None:
            raise CommandError('At least one Organization must be specified')
        #end: if orgQ is None

        #   primary-only filter
        primaryQ = None
        if primary_only:
            primaryQ = Q(is_primary=True)

        #   join everything together
        mainQ = orgQ
        if statusQ is not None:
            mainQ = mainQ & statusQ
        if primaryQ is not None:
            mainQ = mainQ & primaryQ

        # Make our query
        qset = OrganizationUser.objects.filter(mainQ).order_by(
                'user__user__username')

        # And output the results
        for orguser in qset:
            uprof = orguser.user
            user = uprof.user
            if verbosity == 0:
                sys.stdout.write('{}\n'.format(user.username))
            elif verbosity == 1:
                sys.stdout.write('{} ({} {}) <{}>\n'.format(
                    user.username, 
                    user.first_name,
                    user.last_name,
                    user.email,
                    ))
            elif verbosity > 1:
                sys.stdout.write('{} ({} {}) <{}> IsActive:{} '
                        'IsStaff:{} IsSuperUser:{} IsPI:{}\n'.format(
                        user.username,
                        user.first_name,
                        user.last_name,
                        user.email,
                        user.is_active,
                        user.is_staff,
                        user.is_superuser,
                        uprof.is_pi,
                        ))
            #end: if verbosity == 0:
        #end: for orguser in qset:
