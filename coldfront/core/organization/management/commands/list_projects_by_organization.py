import os
import sys

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist

from coldfront.core.utils.common import import_from_settings
from coldfront.core.organization.models import Organization
from coldfront.core.project.models import Project


class Command(BaseCommand):
    help = 'Lists projects belongs to an Organization'

    def add_arguments(self, parser):
        def_delimiter = '|'

        parser.add_argument('-o', '--organization', '--org',
                help='The fullcode of the Organization being queried. '
                    'Maybe repeated to give multiple Organizations (in which '
                    'case any project found in any of them will be listed, '
                    'unless --and is given.',
                action='append',
                default=[],
                )
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

        projects = set()
        for orgcode in orgcodes:
            org = Organization.get_organization_by_fullcode(orgcode)
            if org is None:
                raise CommandError('No Organization with fullcode {} '
                        'found, aborting'.format(orgcode))
            orgs = [ org ]
            if descendents:
                orgs.extend(org.descendents())

            myfilter = { 'organizations__in': orgs }
            if statuses:
                myfilter['status__in'] = statuses
            tmpprojects = Project.objects.filter(**myfilter)

            tmppset = set(tmpprojects.all())
            if andorgs:
                projects = projects.intersection(tmppset)
            else:
                projects = projects.union(tmppset)

        # Convert to list and output
        projects = list(projects)
        projects = sorted(projects, key=lambda x: x.title)
        for project in projects:
            if verbosity:
                sys.stdout.write('{title} ({username}) [{status}]\n'.format(
                    title=project.title,
                    username=project.pi.username,
                    status=project.status.name))
            else:
                sys.stdout.write('{}\n'.format(
                    project.title))
        return
