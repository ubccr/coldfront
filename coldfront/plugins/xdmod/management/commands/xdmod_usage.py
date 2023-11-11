import logging
import os
import sys

from django.core.management.base import BaseCommand
from django.db.models import Q

from coldfront.core.allocation.models import Allocation
from coldfront.core.resource.models import Resource
from coldfront.plugins.xdmod.utils import (XDMOD_ACCOUNT_ATTRIBUTE_NAME,
                                           XDMOD_CLOUD_CORE_TIME_ATTRIBUTE_NAME,
                                           XDMOD_CLOUD_PROJECT_ATTRIBUTE_NAME,
                                           XDMOD_CPU_HOURS_ATTRIBUTE_NAME,
                                           XDMOD_ACC_HOURS_ATTRIBUTE_NAME,
                                           XDMOD_RESOURCE_ATTRIBUTE_NAME,
                                           XDMOD_STORAGE_ATTRIBUTE_NAME,
                                           XDMOD_STORAGE_GROUP_ATTRIBUTE_NAME,
                                           XdmodNotFoundError,
                                           XDModFetcher)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync usage data from XDMoD to ColdFront'
    filter_user = ''
    filter_project = ''
    filter_resource = ''
    filter_account = ''
    sync = False
    print_header = False
    fetch_expired = False

    def add_arguments(self, parser):
        parser.add_argument("-r", "--resource",
            help="Report usage data for specific Resource")
        parser.add_argument("-a", "--account",
            help="Report usage data for specific account")
        parser.add_argument("-u", "--username",
            help="Report usage for specific username")
        parser.add_argument("-p", "--project",
            help="Report usage for specific cloud project")
        parser.add_argument("-s", "--sync",
            help="Update allocation attributes with latest data from XDMoD", action="store_true")
        parser.add_argument("-x", "--header",
            help="Include header in output", action="store_true")
        parser.add_argument("-m", "--statistic",
            help="XDMoD statistic (default total_cpu_hours)",
            default='total_cpu_hours')
        parser.add_argument("--expired",
            help="XDMoD statistic for archived projects", action="store_true")

    def write(self, data):
        try:
            self.stdout.write(data)
        except BrokenPipeError:
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
            sys.exit(1)

    def run_resource_checks(self, resource):
        rname = resource.get_attribute(XDMOD_RESOURCE_ATTRIBUTE_NAME)
        if not rname and resource.parent_resource:
            rname = resource.parent_resource.get_attribute(
                XDMOD_RESOURCE_ATTRIBUTE_NAME)
        if self.filter_resource and self.filter_resource != rname:
            return None
        return rname

    def id_allocation_resources(self, s):
        resources = []
        for r in s.resources.all():
            rname = self.run_resource_checks(r)
            resources.append(rname)
        return resources

    def attribute_check(self, s, attr_name, num=False):
        attr = s.get_attribute(attr_name)
        check_pass = attr
        if num:
            check_pass = attr is not None
        if not check_pass:
            logger.warning("%s attribute not found for allocation: %s",
                        attr_name, s)
            return None
        return attr

    def filter_allocations(self, allocations, account_attr_name=XDMOD_ACCOUNT_ATTRIBUTE_NAME):
        cleared_resources = Resource.objects.filter(
            Q(resourceattribute__resource_attribute_type__name=XDMOD_RESOURCE_ATTRIBUTE_NAME) |
            Q(parent_resource__resourceattribute__resource_attribute_type__name=XDMOD_RESOURCE_ATTRIBUTE_NAME)
            )

        allocations = (
            allocations.select_related('project')
                .prefetch_related(
                    'resources', 'allocationattribute_set', 'allocationuser_set'
                )
                .filter(resources__in=cleared_resources)
            )
        if self.fetch_expired:
            allocations = allocations.filter(~Q(status__name='Active'))
        else:
            allocations = allocations.filter(status__name='Active')

        if self.filter_user:
            allocations = allocations.filter(project__pi__username=self.filter_user)

        if self.filter_project:
            allocations = allocations.filter(
                Q(allocationattribute__allocation_attribute_type__name=XDMOD_CLOUD_PROJECT_ATTRIBUTE_NAME)
                & Q(allocationattribute__value=self.filter_project)
            )

        if self.filter_account:
            allocations = allocations.filter(
                Q(allocationattribute__allocation_attribute_type__name=account_attr_name)
                & Q(allocationattribute__value=self.filter_account)
            )

        return allocations

    def process_total_storage(self):
        header = [
            'allocation_id',
            'pi',
            'account',
            'resources',
            'max_quota',
            'total_storage',
        ]

        if self.print_header:
            self.write('\t'.join(header))

        allocations = Allocation.objects.filter(
            allocationattribute__allocation_attribute_type__name__in=[
                XDMOD_STORAGE_GROUP_ATTRIBUTE_NAME,
                XDMOD_STORAGE_ATTRIBUTE_NAME,
            ]
        )

        allocations = self.filter_allocations(
            allocations, account_attr_name=XDMOD_STORAGE_GROUP_ATTRIBUTE_NAME)

        for s in allocations.distinct():
            account_name = self.attribute_check(s, XDMOD_STORAGE_GROUP_ATTRIBUTE_NAME)
            cpu_hours = self.attribute_check(s, XDMOD_STORAGE_ATTRIBUTE_NAME, num=True)
            if None in [account_name, cpu_hours]:
                continue

            resources = self.id_allocation_resources(s)

            fetcher = XDModFetcher(s.start_date, s.end_date, resources=resources)
            try:
                usage = fetcher.xdmod_fetch_storage(
                        account_name, statistics='avg_physical_usage'
                )
            except XdmodNotFoundError:
                logger.warning(
                    "No data in XDMoD found for allocation %s account %s resources %s",
                    s, account_name, resources)
                continue

            logger.warning(
                    "Total GB = %s for allocation %s account %s GB %s resources %s",
                    usage, s, account_name, cpu_hours, resources)
            if self.sync:
                s.set_usage(XDMOD_STORAGE_ATTRIBUTE_NAME, usage)

            self.write('\t'.join([
                str(s.id),
                s.project.pi.username,
                account_name,
                ','.join(resources),
                str(cpu_hours),
                str(usage),
            ]))


    def process_total_gpu_hours(self):
        header = [
            'allocation_id',
            'pi',
            'account',
            'resources',
            'max_gpu_hours',
            'total_cpu_hours',
        ]

        if self.print_header:
            self.write('\t'.join(header))

        allocations = Allocation.objects.filter(
            allocationattribute__allocation_attribute_type__name__in=[
                XDMOD_ACCOUNT_ATTRIBUTE_NAME,
                XDMOD_ACC_HOURS_ATTRIBUTE_NAME,
            ]
        )
        allocations = self.filter_allocations(allocations)

        for s in allocations.distinct():
            account_name = self.attribute_check(s, XDMOD_ACCOUNT_ATTRIBUTE_NAME)
            cpu_hours = self.attribute_check(s, XDMOD_ACC_HOURS_ATTRIBUTE_NAME, num=True)
            if None in [account_name, cpu_hours]:
                continue

            resources = self.id_allocation_resources(s)

            fetcher = XDModFetcher(s.start_date, s.end_date, resources=resources)
            try:
                usage = fetcher.xdmod_fetch_cpu_hours(
                        account_name, statistics='total_gpu_hours'
                )
            except XdmodNotFoundError:
                logger.warning(
                    "No data in XDMoD found for allocation %s account %s resources %s",
                    s, account_name, resources)
                continue

            logger.warning(
                "Total Accelerator hours = %s for allocation %s account %s gpu_hours %s resources %s",
                        usage, s, account_name, cpu_hours, resources)
            if self.sync:
                s.set_usage(XDMOD_ACC_HOURS_ATTRIBUTE_NAME, usage)

            self.write('\t'.join([
                str(s.id),
                s.project.pi.username,
                account_name,
                ','.join(resources),
                str(cpu_hours),
                str(usage),
            ]))

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

        allocations = Allocation.objects.filter(
            allocationattribute__allocation_attribute_type__name__in=[
                XDMOD_ACCOUNT_ATTRIBUTE_NAME,
                XDMOD_CPU_HOURS_ATTRIBUTE_NAME,
            ]
        )
        allocations = self.filter_allocations(allocations)

        resource_filter = (
            Q(resourceattribute__resource_attribute_type__name=XDMOD_RESOURCE_ATTRIBUTE_NAME) |
            Q(parent_resource__resourceattribute__resource_attribute_type__name=XDMOD_RESOURCE_ATTRIBUTE_NAME)
        )
        resources_all = Resource.objects.filter(
            id__in=[r.id for a in allocations for r in a.resources.all()]).filter(
            resource_filter
        )

        # fetcher = XDModFetcher(resources=resources_all)
        # try:
        #     usage = fetcher.xdmod_fetch_all_project_usages('total_cpu_hours')
        # except XdmodNotFoundError:
        #     raise XdmodNotFoundError(
        #         "No data in XDMoD found for resources %s", resources_all)

        for s in allocations.distinct():
            account_name = self.attribute_check(s, XDMOD_ACCOUNT_ATTRIBUTE_NAME)
            cpu_hours = self.attribute_check(s, XDMOD_CPU_HOURS_ATTRIBUTE_NAME, num=True)
            if None in [account_name, cpu_hours]:
                continue

            resources = self.id_allocation_resources(s)

            fetcher = XDModFetcher(s.start_date, s.end_date, resources=resources)
            try:
                usage = fetcher.xdmod_fetch_cpu_hours(account_name)
            except XdmodNotFoundError:
                logger.warning(
                    "No data in XDMoD found for allocation %s account %s resources %s",
                    s, account_name, resources)
                continue

            logger.warning(
                    "Total CPU hours = %s for allocation %s account %s cpu_hours %s resources %s",
                        usage, s, account_name, cpu_hours, resources)
            if self.sync:
                cpu_hours_attr = s.allocationattribute_set.get(
                    allocation_attribute_type__name=XDMOD_CPU_HOURS_ATTRIBUTE_NAME)
                cpu_hours_attr.value = usage
                cpu_hours_attr.save()
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

        allocations = Allocation.objects.filter(
            allocationattribute__allocation_attribute_type__name__in=[
                XDMOD_CLOUD_PROJECT_ATTRIBUTE_NAME,
                XDMOD_CLOUD_CORE_TIME_ATTRIBUTE_NAME,
            ]
        )
        allocations = self.filter_allocations(allocations)

        for s in allocations.distinct():
            project_name = self.attribute_check(
                s, XDMOD_CLOUD_PROJECT_ATTRIBUTE_NAME)
            core_time = self.attribute_check(
                s, XDMOD_CLOUD_CORE_TIME_ATTRIBUTE_NAME, num=True)
            if None in [project_name, core_time]:
                continue
            resources = self.id_allocation_resources(s)

            fetcher = XDModFetcher(s.start_date, s.end_date, resources=resources)
            try:
                usage = fetcher.xdmod_fetch_cloud_core_time(project_name)
            except XdmodNotFoundError:
                logger.warning(
                    "No data in XDMoD found for allocation %s project %s resources %s",
                    s, project_name, resources)
                continue

            logger.warning(
                "Cloud core time = %s for allocation %s project %s core_time %s resources %s",
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
        verbosity_dict = {
            0:logging.ERROR,
            1:logging.WARN,
            2:logging.INFO,
            3:logging.DEBUG
        }
        root_logger.setLevel(verbosity_dict[verbosity])

        if options['sync']:
            self.sync = True
            logger.warning("Syncing ColdFront with XDMoD")

        filters = {
            'username': self.filter_user,
            'account': self.filter_account,
            'project': self.filter_project,
            'resource': self.filter_resource,
        }
        for filter_name, filter_attr in filters.items():
            if options[filter_name]:
                logger.info("Filtering output by %s: %s", filter_name, options[filter_name])
                filter_attr = options[filter_name]

        bool_opts = {
            'header':self.print_header,
            'expired':self.fetch_expired,
        }
        for opt, attribute in bool_opts.items():
            if options[opt]:
                attribute = True

        statistic = 'total_cpu_hours'
        if options['statistic']:
            statistic = options['statistic']

        if statistic == 'total_cpu_hours':
            self.process_total_cpu_hours()
        elif statistic == 'cloud_core_time':
            self.process_cloud_core_time()
        elif statistic == 'total_acc_hours':
            self.process_total_gpu_hours()
        elif statistic == 'total_storage':
            self.process_total_storage()
        else:
            logger.error("Unsupported XDMoD statistic")
            sys.exit(1)
