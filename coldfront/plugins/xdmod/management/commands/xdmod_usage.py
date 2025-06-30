# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import os
import sys

from django.core.management.base import BaseCommand
from django.db.models import Q

from coldfront.core.allocation.models import Allocation
from coldfront.plugins.xdmod.utils import (
    XDMOD_ACC_HOURS_ATTRIBUTE_NAME,
    XDMOD_ACCOUNT_ATTRIBUTE_NAME,
    XDMOD_CLOUD_CORE_TIME_ATTRIBUTE_NAME,
    XDMOD_CLOUD_PROJECT_ATTRIBUTE_NAME,
    XDMOD_CPU_HOURS_ATTRIBUTE_NAME,
    XDMOD_RESOURCE_ATTRIBUTE_NAME,
    XDMOD_STORAGE_ATTRIBUTE_NAME,
    XDMOD_STORAGE_GROUP_ATTRIBUTE_NAME,
    XdmodNotFoundError,
    xdmod_fetch_cloud_core_time,
    xdmod_fetch_total_cpu_hours,
    xdmod_fetch_total_storage,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Sync usage data from XDMoD to ColdFront"

    def add_arguments(self, parser):
        parser.add_argument("-r", "--resource", help="Report usage data for specific Resource")
        parser.add_argument("-a", "--account", help="Report usage data for specific account")
        parser.add_argument("-u", "--username", help="Report usage for specific username")
        parser.add_argument("-p", "--project", help="Report usage for specific cloud project")
        parser.add_argument(
            "-s", "--sync", help="Update allocation attributes with latest data from XDMoD", action="store_true"
        )
        parser.add_argument("-x", "--header", help="Include header in output", action="store_true")
        parser.add_argument("-m", "--statistic", help="XDMoD statistic (default total_cpu_hours)", required=True)
        parser.add_argument("--expired", help="XDMoD statistic for archived projects", action="store_true")

    def write(self, data):
        try:
            self.stdout.write(data)
        except BrokenPipeError:
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
            sys.exit(1)

    def process_total_storage(self):
        header = [
            "allocation_id",
            "pi",
            "account",
            "resources",
            "max_quota",
            "total_storage",
        ]

        if self.print_header:
            self.write("\t".join(header))

        allocations = Allocation.objects.prefetch_related(
            "project", "resources", "allocationattribute_set", "allocationuser_set"
        ).filter(
            allocationattribute__allocation_attribute_type__name__in=[
                XDMOD_STORAGE_GROUP_ATTRIBUTE_NAME,
                XDMOD_STORAGE_ATTRIBUTE_NAME,
            ]
        )

        if self.fetch_expired:
            allocations = allocations.filter(
                ~Q(status__name="Active"),
            )
        else:
            allocations = allocations.filter(
                status__name="Active",
            )

        if self.filter_user:
            allocations = allocations.filter(project__pi__username=self.filter_user)

        if self.filter_account:
            allocations = allocations.filter(
                Q(allocationattribute__allocation_attribute_type__name=XDMOD_STORAGE_GROUP_ATTRIBUTE_NAME)
                & Q(allocationattribute__value=self.filter_account)
            )

        for s in allocations.distinct():
            account_name = s.get_attribute(XDMOD_STORAGE_GROUP_ATTRIBUTE_NAME)
            if not account_name:
                logger.warning("%s attribute not found for allocation: %s", XDMOD_STORAGE_GROUP_ATTRIBUTE_NAME, s)
                continue

            cpu_hours = s.get_attribute(XDMOD_STORAGE_ATTRIBUTE_NAME)
            if not cpu_hours:
                logger.warning("%s attribute not found for allocation: %s", XDMOD_STORAGE_ATTRIBUTE_NAME, s)
                continue

            resources = []
            for r in s.resources.all():
                rname = r.get_attribute(XDMOD_RESOURCE_ATTRIBUTE_NAME)
                if not rname and r.parent_resource:
                    rname = r.parent_resource.get_attribute(XDMOD_RESOURCE_ATTRIBUTE_NAME)

                if not rname:
                    continue

                if self.filter_resource and self.filter_resource != rname:
                    continue

                resources.append(rname)

            if len(resources) == 0:
                logger.warning(
                    "%s attribute not found on any resouces for allocation: %s", XDMOD_RESOURCE_ATTRIBUTE_NAME, s
                )
                continue

            try:
                usage = xdmod_fetch_total_storage(
                    s.start_date, s.end_date, account_name, resources=resources, statistics="avg_physical_usage"
                )
            except XdmodNotFoundError:
                logger.warning(
                    "No data in XDMoD found for allocation %s account %s resources %s", s, account_name, resources
                )
                continue

            logger.warning(
                "Total GB = %s for allocation %s account %s GB %s resources %s",
                usage,
                s,
                account_name,
                cpu_hours,
                resources,
            )
            if self.sync:
                s.set_usage(XDMOD_STORAGE_ATTRIBUTE_NAME, usage)

            self.write(
                "\t".join(
                    [
                        str(s.id),
                        s.project.pi.username,
                        account_name,
                        ",".join(resources),
                        str(cpu_hours),
                        str(usage),
                    ]
                )
            )

    def process_total_gpu_hours(self):
        header = [
            "allocation_id",
            "pi",
            "account",
            "resources",
            "max_gpu_hours",
            "total_cpu_hours",
        ]

        if self.print_header:
            self.write("\t".join(header))

        allocations = Allocation.objects.prefetch_related(
            "project", "resources", "allocationattribute_set", "allocationuser_set"
        ).filter(
            allocationattribute__allocation_attribute_type__name__in=[
                XDMOD_ACCOUNT_ATTRIBUTE_NAME,
                XDMOD_ACC_HOURS_ATTRIBUTE_NAME,
            ]
        )

        if self.fetch_expired:
            allocations = allocations.filter(
                ~Q(status__name="Active"),
            )
        else:
            allocations = allocations.filter(
                status__name="Active",
            )

        if self.filter_user:
            allocations = allocations.filter(project__pi__username=self.filter_user)

        if self.filter_account:
            allocations = allocations.filter(
                Q(allocationattribute__allocation_attribute_type__name=XDMOD_ACCOUNT_ATTRIBUTE_NAME)
                & Q(allocationattribute__value=self.filter_account)
            )

        for s in allocations.distinct():
            account_name = s.get_attribute(XDMOD_ACCOUNT_ATTRIBUTE_NAME)
            if not account_name:
                logger.warning("%s attribute not found for allocation: %s", XDMOD_ACCOUNT_ATTRIBUTE_NAME, s)
                continue

            cpu_hours = s.get_attribute(XDMOD_ACC_HOURS_ATTRIBUTE_NAME)
            if not cpu_hours:
                logger.warning("%s attribute not found for allocation: %s", XDMOD_ACC_HOURS_ATTRIBUTE_NAME, s)
                continue

            resources = []
            for r in s.resources.all():
                rname = r.get_attribute(XDMOD_RESOURCE_ATTRIBUTE_NAME)
                if not rname and r.parent_resource:
                    rname = r.parent_resource.get_attribute(XDMOD_RESOURCE_ATTRIBUTE_NAME)

                if not rname:
                    continue

                if self.filter_resource and self.filter_resource != rname:
                    continue

                resources.append(rname)

            if len(resources) == 0:
                logger.warning(
                    "%s attribute not found on any resouces for allocation: %s", XDMOD_RESOURCE_ATTRIBUTE_NAME, s
                )
                continue

            try:
                usage = xdmod_fetch_total_cpu_hours(
                    s.start_date, s.end_date, account_name, resources=resources, statistics="total_gpu_hours"
                )
            except XdmodNotFoundError:
                logger.warning(
                    "No data in XDMoD found for allocation %s account %s resources %s", s, account_name, resources
                )
                continue

            logger.warning(
                "Total Accelerator hours = %s for allocation %s account %s gpu_hours %s resources %s",
                usage,
                s,
                account_name,
                cpu_hours,
                resources,
            )
            if self.sync:
                s.set_usage(XDMOD_ACC_HOURS_ATTRIBUTE_NAME, usage)

            self.write(
                "\t".join(
                    [
                        str(s.id),
                        s.project.pi.username,
                        account_name,
                        ",".join(resources),
                        str(cpu_hours),
                        str(usage),
                    ]
                )
            )

    def process_total_cpu_hours(self):
        header = [
            "allocation_id",
            "pi",
            "account",
            "resources",
            "max_cpu_hours",
            "total_cpu_hours",
        ]

        if self.print_header:
            self.write("\t".join(header))

        allocations = (
            Allocation.objects.prefetch_related("project", "resources", "allocationattribute_set", "allocationuser_set")
            .filter(
                status__name="Active",
            )
            .filter(
                allocationattribute__allocation_attribute_type__name__in=[
                    XDMOD_ACCOUNT_ATTRIBUTE_NAME,
                    XDMOD_CPU_HOURS_ATTRIBUTE_NAME,
                ]
            )
        )

        if self.filter_user:
            allocations = allocations.filter(project__pi__username=self.filter_user)

        if self.filter_account:
            allocations = allocations.filter(
                Q(allocationattribute__allocation_attribute_type__name=XDMOD_ACCOUNT_ATTRIBUTE_NAME)
                & Q(allocationattribute__value=self.filter_account)
            )

        for s in allocations.distinct():
            account_name = s.get_attribute(XDMOD_ACCOUNT_ATTRIBUTE_NAME)
            if not account_name:
                logger.warning("%s attribute not found for allocation: %s", XDMOD_ACCOUNT_ATTRIBUTE_NAME, s)
                continue

            cpu_hours = s.get_attribute(XDMOD_CPU_HOURS_ATTRIBUTE_NAME)
            if not cpu_hours:
                logger.warning("%s attribute not found for allocation: %s", XDMOD_CPU_HOURS_ATTRIBUTE_NAME, s)
                continue

            resources = []
            for r in s.resources.all():
                rname = r.get_attribute(XDMOD_RESOURCE_ATTRIBUTE_NAME)
                if not rname and r.parent_resource:
                    rname = r.parent_resource.get_attribute(XDMOD_RESOURCE_ATTRIBUTE_NAME)

                if not rname:
                    continue

                if self.filter_resource and self.filter_resource != rname:
                    continue

                resources.append(rname)

            if len(resources) == 0:
                logger.warning(
                    "%s attribute not found on any resouces for allocation: %s", XDMOD_RESOURCE_ATTRIBUTE_NAME, s
                )
                continue

            try:
                usage = xdmod_fetch_total_cpu_hours(s.start_date, s.end_date, account_name, resources=resources)
            except XdmodNotFoundError:
                logger.warning(
                    "No data in XDMoD found for allocation %s account %s resources %s", s, account_name, resources
                )
                continue

            logger.warning(
                "Total CPU hours = %s for allocation %s account %s cpu_hours %s resources %s",
                usage,
                s,
                account_name,
                cpu_hours,
                resources,
            )
            if self.sync:
                s.set_usage(XDMOD_CPU_HOURS_ATTRIBUTE_NAME, usage)

            self.write(
                "\t".join(
                    [
                        str(s.id),
                        s.project.pi.username,
                        account_name,
                        ",".join(resources),
                        str(cpu_hours),
                        str(usage),
                    ]
                )
            )

    def process_cloud_core_time(self):
        header = [
            "allocation_id",
            "pi",
            "project",
            "resources",
            "max_core_time",
            "cloud_core_time",
        ]

        if self.print_header:
            self.write("\t".join(header))

        allocations = (
            Allocation.objects.prefetch_related("project", "resources", "allocationattribute_set", "allocationuser_set")
            .filter(
                status__name="Active",
            )
            .filter(
                allocationattribute__allocation_attribute_type__name__in=[
                    XDMOD_CLOUD_PROJECT_ATTRIBUTE_NAME,
                    XDMOD_CLOUD_CORE_TIME_ATTRIBUTE_NAME,
                ]
            )
        )

        if self.filter_user:
            allocations = allocations.filter(project__pi__username=self.filter_user)

        if self.filter_project:
            allocations = allocations.filter(
                Q(allocationattribute__allocation_attribute_type__name=XDMOD_CLOUD_PROJECT_ATTRIBUTE_NAME)
                & Q(allocationattribute__value=self.filter_project)
            )

        for s in allocations.distinct():
            project_name = s.get_attribute(XDMOD_CLOUD_PROJECT_ATTRIBUTE_NAME)
            if not project_name:
                logger.warning("%s attribute not found for allocation: %s", XDMOD_CLOUD_PROJECT_ATTRIBUTE_NAME, s)
                continue

            core_time = s.get_attribute(XDMOD_CLOUD_CORE_TIME_ATTRIBUTE_NAME)
            if not core_time:
                logger.warning("%s attribute not found for allocation: %s", XDMOD_CLOUD_CORE_TIME_ATTRIBUTE_NAME, s)
                continue

            resources = []
            for r in s.resources.all():
                rname = r.get_attribute(XDMOD_RESOURCE_ATTRIBUTE_NAME)
                if not rname and r.parent_resource:
                    rname = r.parent_resource.get_attribute(XDMOD_RESOURCE_ATTRIBUTE_NAME)

                if not rname:
                    continue

                if self.filter_resource and self.filter_resource != rname:
                    continue

                resources.append(rname)

            if len(resources) == 0:
                logger.warning(
                    "%s attribute not found on any resouces for allocation: %s", XDMOD_RESOURCE_ATTRIBUTE_NAME, s
                )
                continue

            try:
                usage = xdmod_fetch_cloud_core_time(s.start_date, s.end_date, project_name, resources=resources)
            except XdmodNotFoundError:
                logger.warning(
                    "No data in XDMoD found for allocation %s project %s resources %s", s, project_name, resources
                )
                continue

            logger.warning(
                "Cloud core time = %s for allocation %s project %s core_time %s resources %s",
                usage,
                s,
                project_name,
                core_time,
                resources,
            )
            if self.sync:
                s.set_usage(XDMOD_CLOUD_CORE_TIME_ATTRIBUTE_NAME, usage)

            self.write(
                "\t".join(
                    [
                        str(s.id),
                        s.project.pi.username,
                        project_name,
                        ",".join(resources),
                        str(core_time),
                        str(usage),
                    ]
                )
            )

    def handle(self, *args, **options):
        verbosity = int(options["verbosity"])
        root_logger = logging.getLogger("")
        if verbosity == 0:
            root_logger.setLevel(logging.ERROR)
        elif verbosity == 2:
            root_logger.setLevel(logging.INFO)
        elif verbosity == 3:
            root_logger.setLevel(logging.DEBUG)
        else:
            root_logger.setLevel(logging.WARNING)

        self.sync = False
        if options["sync"]:
            self.sync = True
            logger.warning("Syncing ColdFront with XDMoD")

        statistic = "total_cpu_hours"
        self.filter_user = ""
        self.filter_project = ""
        self.filter_resource = ""
        self.filter_account = ""
        self.print_header = False
        self.fetch_expired = False

        if options["username"]:
            logger.info("Filtering output by username: %s", options["username"])
            self.filter_user = options["username"]
        if options["account"]:
            logger.info("Filtering output by account: %s", options["account"])
            self.filter_account = options["account"]
        if options["project"]:
            logger.info("Filtering output by project: %s", options["project"])
            self.filter_project = options["project"]
        if options["resource"]:
            logger.info("Filtering output by resource: %s", options["resource"])
            self.filter_resource = options["resource"]
        if options["header"]:
            self.print_header = True

        if options["expired"]:
            self.fetch_expired = True

        if options["statistic"]:
            statistic = options["statistic"]

        if statistic == "total_cpu_hours":
            self.process_total_cpu_hours()
        elif statistic == "cloud_core_time":
            self.process_cloud_core_time()
        elif statistic == "total_acc_hours":
            self.process_total_gpu_hours()
        elif statistic == "total_storage":
            self.process_total_storage()
        else:
            logger.error("Unsupported XDMoD statistic")
            sys.exit(1)
