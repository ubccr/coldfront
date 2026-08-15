# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Management command to import a Slurm cluster from a slurm.conf file or REST API.

Usage::

    coldfront slurm_import_cluster --slurm-conf /path/to/slurm.conf
    coldfront slurm_import_cluster --slurm-conf /path/to/slurm.conf --noop
    coldfront slurm_import_cluster --slurm-conf /path/to/slurm.conf --update
    coldfront slurm_import_cluster --cluster-name snowflake
    coldfront slurm_import_cluster --cluster-name snowflake --noop

Either ``--slurm-conf`` or ``--cluster-name`` must be provided.
"""

from __future__ import annotations

import logging

from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Import a Slurm cluster from a slurm.conf file or REST API"

    def add_arguments(self, parser):
        parser.add_argument(
            "--slurm-conf",
            help=_("Path to a slurm.conf file to import"),
        )
        parser.add_argument(
            "--cluster-name",
            help=_("Cluster name to import from the Slurm REST API"),
        )
        parser.add_argument(
            "--noop",
            action="store_true",
            help=_("Show what would be imported without writing to the database"),
        )
        parser.add_argument(
            "--update",
            action="store_true",
            help=_("Update existing records (default is to create only)"),
        )

    def handle(self, *args, **options):
        conf_path = options.get("slurm_conf")
        cluster_name = options.get("cluster_name")
        noop = options.get("noop", False)
        update = options.get("update", False)

        if not conf_path and not cluster_name:
            raise CommandError("Either --slurm-conf or --cluster-name must be provided")

        if conf_path:
            self._import_from_conf(conf_path, noop, update)
        else:
            self._import_from_api(cluster_name, noop, update)

    def _import_from_conf(self, conf_path: str, noop: bool, update: bool) -> None:
        from coldfront.slurm.sync import import_cluster_from_conf

        self.stdout.write(self.style.NOTICE(f"Importing cluster from {conf_path}"))

        report = import_cluster_from_conf(
            conf_path=conf_path,
            noop=noop,
            update=update,
        )

        self._print_report(report)

    def _import_from_api(self, cluster_name: str, noop: bool, update: bool) -> None:
        from coldfront.slurm.sync import import_cluster_from_api

        self.stdout.write(self.style.NOTICE(f"Importing cluster '{cluster_name}' from Slurm REST API"))

        report = import_cluster_from_api(
            cluster_name=cluster_name,
            noop=noop,
            update=update,
        )

        self._print_report(report)

    def _print_report(self, report) -> None:
        if report.success:
            self.stdout.write(
                self.style.SUCCESS(
                    f"[OK] {report.cluster}: "
                    f"cluster {'created' if report.cluster_created else 'updated' if report.cluster_updated else 'found'}, "  # noqa: E501
                    f"{report.partitions_created} partitions created, "
                    f"{report.partitions_updated} partitions updated, "
                    f"{report.qos_created} QOS created, "
                    f"{report.qos_found} QOS found"
                )
            )
        else:
            self.stdout.write(self.style.ERROR(f"[FAIL] {report.cluster}: {'; '.join(report.errors)}"))

        for w in report.warnings:
            self.stdout.write(self.style.WARNING(f"  warn: {w}"))
