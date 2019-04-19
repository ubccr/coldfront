import logging
import os
import sys
import tempfile

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from coldfront.core.allocation.models import Allocation
from coldfront.core.utils.common import import_from_settings
from coldfront.plugins.xdmod.utils import (XDMOD_ACCOUNT_ATTRIBUTE_NAME,
                                           XDMOD_CLOUD_CORE_TIME_ATTRIBUTE_NAME,
                                           XDMOD_CLOUD_PROJECT_ATTRIBUTE_NAME,
                                           XDMOD_CPU_HOURS_ATTRIBUTE_NAME,
                                           XDMOD_RESOURCE_ATTRIBUTE_NAME,
                                           XdmodError, XdmodNotFoundError,
                                           xdmod_fetch_cloud_core_time,
                                           xdmod_fetch_total_cpu_hours)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync usage data from XDMoD to ColdFront'

    def add_arguments(self, parser):
        parser.add_argument("-r", "--resource",
                            help="Report usage data for specific Resource")
        parser.add_argument("-a", "--account",
                            help="Report usage data for specific account")
        parser.add_argument("-u", "--username",
                            help="Report usage for specific username")
        parser.add_argument("-p", "--project",
                            help="Report usage for specific cloud project")
        parser.add_argument(
            "-s", "--sync", help="Update allocation attributes with latest data from XDMoD", action="store_true")
        parser.add_argument(
            "-x", "--header", help="Include header in output", action="store_true")
        parser.add_argument(
            "-m", "--statistic", help="XDMoD statistic (default total_cpu_hours)", required=True)

    def write(self, data):
        try:
            self.stdout.write(data)
        except BrokenPipeError:
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
            sys.exit(1)

    def process_total_cpu_hours(self):
        header = [
            'allocation_id',
            'pi',
            'account',
            'resources',
            'max_cpu_hours',
            'total_cpu_hours',
        ]

        if self.print_header:
            self.write('\t'.join(header))

        allocations = Allocation.objects.prefetch_related(
            'project',
            'resources',
            'allocationattribute_set',
            'allocationuser_set'
        ).filter(
            status__name='Active',
        ).filter(
            allocationattribute__allocation_attribute_type__name__in=[
                XDMOD_ACCOUNT_ATTRIBUTE_NAME,
                XDMOD_CPU_HOURS_ATTRIBUTE_NAME,
            ]
        )

        if self.filter_user:
            allocations = allocations.filter(project__pi__username=self.filter_user)

        if self.filter_account:
            allocations = allocations.filter(
                Q(allocationattribute__allocation_attribute_type__name=XDMOD_ACCOUNT_ATTRIBUTE_NAME) &
                Q(allocationattribute__value=self.filter_account)
            )

        for s in allocations.distinct():
            account_name = s.get_attribute(XDMOD_ACCOUNT_ATTRIBUTE_NAME)
            if not account_name:
                logger.warn("%s attribute not found for allocation: %s",
                            XDMOD_ACCOUNT_ATTRIBUTE_NAME, s)
                continue

            cpu_hours = s.get_attribute(XDMOD_CPU_HOURS_ATTRIBUTE_NAME)
            if not cpu_hours:
                logger.warn("%s attribute not found for allocation: %s",
                            XDMOD_CPU_HOURS_ATTRIBUTE_NAME, s)
                continue

            resources = []
            for r in s.resources.all():
                rname = r.get_attribute(XDMOD_RESOURCE_ATTRIBUTE_NAME)
                if not rname and r.parent_resource:
                    rname = r.parent_resource.get_attribute(
                        XDMOD_RESOURCE_ATTRIBUTE_NAME)

                if not rname:
                    continue

                if self.filter_resource and self.filter_resource != rname:
                    continue

                resources.append(rname)

            if len(resources) == 0:
                logger.warn("%s attribute not found on any resouces for allocation: %s",
                            XDMOD_RESOURCE_ATTRIBUTE_NAME, s)
                continue

            try:
                usage = xdmod_fetch_total_cpu_hours(
                    s.start_date, s.end_date, account_name, resources=resources)
            except XdmodNotFoundError:
                logger.warn(
                    "No data in XDMoD found for allocation %s account %s resources %s", s, account_name, resources)
                continue

            logger.warn("Total CPU hours = %s for allocation %s account %s cpu_hours %s resources %s",
                        usage, s, account_name, cpu_hours, resources)
            if self.sync:
                s.set_usage(XDMOD_CPU_HOURS_ATTRIBUTE_NAME, usage)

            self.write('\t'.join([
                str(s.id),
                s.project.pi.username,
                account_name,
                ','.join(resources),
                str(cpu_hours),
                str(usage),
            ]))

    def process_cloud_core_time(self):
        header = [
            'allocation_id',
            'pi',
            'project',
            'resources',
            'max_core_time',
            'cloud_core_time',
        ]

        if self.print_header:
            self.write('\t'.join(header))

        allocations = Allocation.objects.prefetch_related(
            'project',
            'resources',
            'allocationattribute_set',
            'allocationuser_set'
        ).filter(
            status__name='Active',
        ).filter(
            allocationattribute__allocation_attribute_type__name__in=[
                XDMOD_CLOUD_PROJECT_ATTRIBUTE_NAME,
                XDMOD_CLOUD_CORE_TIME_ATTRIBUTE_NAME,
            ]
        )

        if self.filter_user:
            allocations = allocations.filter(project__pi__username=self.filter_user)

        if self.filter_project:
            allocations = allocations.filter(
                Q(allocationattribute__allocation_attribute_type__name=XDMOD_CLOUD_PROJECT_ATTRIBUTE_NAME) &
                Q(allocationattribute__value=self.filter_project)
            )

        for s in allocations.distinct():
            project_name = s.get_attribute(XDMOD_CLOUD_PROJECT_ATTRIBUTE_NAME)
            if not project_name:
                logger.warn("%s attribute not found for allocation: %s",
                            XDMOD_CLOUD_PROJECT_ATTRIBUTE_NAME, s)
                continue

            core_time = s.get_attribute(XDMOD_CLOUD_CORE_TIME_ATTRIBUTE_NAME)
            if not core_time:
                logger.warn("%s attribute not found for allocation: %s",
                            XDMOD_CLOUD_CORE_TIME_ATTRIBUTE_NAME, s)
                continue

            resources = []
            for r in s.resources.all():
                rname = r.get_attribute(XDMOD_RESOURCE_ATTRIBUTE_NAME)
                if not rname and r.parent_resource:
                    rname = r.parent_resource.get_attribute(
                        XDMOD_RESOURCE_ATTRIBUTE_NAME)

                if not rname:
                    continue

                if self.filter_resource and self.filter_resource != rname:
                    continue

                resources.append(rname)

            if len(resources) == 0:
                logger.warn("%s attribute not found on any resouces for allocation: %s",
                            XDMOD_RESOURCE_ATTRIBUTE_NAME, s)
                continue

            try:
                usage = xdmod_fetch_cloud_core_time(
                    s.start_date, s.end_date, project_name, resources=resources)
            except XdmodNotFoundError:
                logger.warn(
                    "No data in XDMoD found for allocation %s project %s resources %s", s, project_name, resources)
                continue

            logger.warn("Cloud core time = %s for allocation %s project %s core_time %s resources %s",
                        usage, s, project_name, core_time, resources)
            if self.sync:
                s.set_usage(XDMOD_CLOUD_CORE_TIME_ATTRIBUTE_NAME, usage)

            self.write('\t'.join([
                str(s.id),
                s.project.pi.username,
                project_name,
                ','.join(resources),
                str(core_time),
                str(usage),
            ]))

    def handle(self, *args, **options):
        verbosity = int(options['verbosity'])
        root_logger = logging.getLogger('')
        if verbosity == 0:
            root_logger.setLevel(logging.ERROR)
        elif verbosity == 2:
            root_logger.setLevel(logging.INFO)
        elif verbosity == 3:
            root_logger.setLevel(logging.DEBUG)
        else:
            root_logger.setLevel(logging.WARN)

        self.sync = False
        if options['sync']:
            self.sync = True
            logger.warn("Syncing ColdFront with XDMoD")

        statistic = 'total_cpu_hours'
        self.filter_user = ''
        self.filter_project = ''
        self.filter_resource = ''
        self.filter_account = ''
        self.print_header = False
        if options['username']:
            logger.info("Filtering output by username: %s",
                        options['username'])
            self.filter_user = options['username']
        if options['account']:
            logger.info("Filtering output by account: %s", options['account'])
            self.filter_account = options['account']
        if options['project']:
            logger.info("Filtering output by project: %s", options['project'])
            self.filter_project = options['project']
        if options['resource']:
            logger.info("Filtering output by resource: %s",
                        options['resource'])
            self.filter_resource = options['resource']
        if options['header']:
            self.print_header = True
        if options['statistic']:
            statistic = options['statistic']

        if statistic == 'total_cpu_hours':
            self.process_total_cpu_hours()
        elif statistic == 'cloud_core_time':
            self.process_cloud_core_time()
        else:
            logger.error("Unsupported XDMoD statistic")
            sys.exit(1)
