import os
import sys

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q

from coldfront.core.organization.models import (
            Organization, 
            OrganizationProject,
        )
from coldfront.core.project.models import (
            ProjectStatusChoice,
        )


class Command(BaseCommand):
    help = 'Lists projects belongs to an Organization'

    def add_arguments(self, parser):
        parser.add_argument('-o', '--organization', '--org',
                help='The fullcode of the Organization being queried. '
                    'Maybe repeated to give multiple Organizations (in which '
                    'case any project found in any of them will be listed, '
                    'unless --and is given.',
                action='append',
                default=[],
                )
        parser.add_argument('--primary_only', '--primary-only',
                '--primary_organization_only', '--primary_organization',
                '--primary-organization-only', '--primary-organization', 
                '--primary_org', '--primary-org',
                '--primaryorg', '--primary',
                help='If set, only consider primary organizations in '
                    'matching projects.  Normally we match projects if '
                    'either primary or additional_organizations match.',
                action='store_true',)
        parser.add_argument('--and',
                help='If multiple Organizations are given, only list projects '
                    'which are found in all of them.  Default is to list '
                    'projects in any of them',
                action='store_true',)
        parser.add_argument('--descendents', '--children', '-c',
                help='If set, then when matching against a given fullcode of '
                    'an Organization, we consider an project to match if the '
                    'project belongs to any Organization descended from the '
                    'named Organization.  If unset (default), an project '
                    'matches only if it belongs to the named Organization.',
                action='store_true',
                )
        parser.add_argument('--status', '-s',
                help='By default, all matching projects are displayed.  If '
                    'a status is given, only matching projects with a matching '
                    'status are displayed.  This can be repeated to allow '
                    'matching multiple statuses',
                action='append',
                default=[],
                )
        return


    def handle(self, *args, **options):

        orgcodes = options['organization']
        andorgs = options['and']
        verbosity = options['verbosity']
        descendents = options['descendents']
        statuses = options['status']
        primary_only = options['primary_only']

        # Generate our filter

        #   status filter
        statusQ = None
        if statuses:
            # User only wants specified statuses
            statuslist = []
            for sname in statuses:
                status = ProjectStatusChoice.objects.get(name=sname)
                statuslist.append(status)
            statusQ = Q(organization__status__in=statuslist)


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
            elif andOrgs:
                orgQ = orgQ & orgcodeQ
            else:
                orgQ = orgQ | orgcodeQ
            #end: if orgQ is None
        #end: for orgcode
        if orgQ is None:
            raise CommandError('At least one Organization must be specified.')
        #end: if orgQ is None:

        #   primary only filter
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
        qset = OrganizationProject.objects.filter(mainQ).order_by('project__title')

        # And output the results
        for orgproj in qset:
            project = orgproj.project
            if verbosity:
                sys.stdout.write('{title} ({username}) [{status}]\n'.format(
                    title=project.title,
                    username=project.pi.username,
                    status=project.status.name))
            else:
                sys.stdout.write('{}\n'.format(
                    project.title))
            #end: if verbosity
        #end: for orgproj

        return
