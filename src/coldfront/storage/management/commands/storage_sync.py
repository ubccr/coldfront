# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Management command to synchronize ColdFront Storage models with storage
system backends.

Usage::

    coldfront storage_sync                          # sync all clusters
    coldfront storage_sync --cluster 3              # sync a single cluster by pk
    coldfront storage_sync --cluster hpc01          # sync a single cluster by name
    coldfront storage_sync --dry-run                # show what would change
    coldfront storage_sync --cluster hpc01 --dry-run

This command runs synchronously and calls the same reconciliation code
path (``sync_storage_clusters``) as the system jobs.  Clusters without a
backend are skipped and reported as OK.
"""

import logging
import sys
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from coldfront.storage.models import StorageCluster

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Synchronize ColdFront Storage models with storage backends"

    def add_arguments(self, parser):
        parser.add_argument(
            "--cluster",
            help="Cluster PK or name. Syncs all clusters when omitted.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would change without making API calls.",
        )

    @staticmethod
    def _configure_storage_logging(verbosity: int) -> None:
        """Configure the ``coldfront.storage`` logger based on verbosity.

        - verbosity >= 3: DEBUG level, console handler attached, propagation disabled
        - verbosity >= 2: INFO  level, console handler attached, propagation disabled
        - verbosity <= 1: WARNING level, any attached console handler removed, propagation enabled

        The console handler writes to stderr to match Django management command output.
        """
        storage_logger = logging.getLogger("coldfront.storage")

        # Find any console handler we may have attached on a previous run
        # (or from LOGGING config).  We only manage StreamHandler instances
        # that write to stderr.
        console_handlers = [
            h for h in storage_logger.handlers if isinstance(h, logging.StreamHandler) and h.stream is sys.stderr
        ]

        if verbosity >= 2:
            # Set level and attach console handler if not already present
            level = logging.DEBUG if verbosity >= 3 else logging.INFO
            storage_logger.setLevel(level)
            if not console_handlers:
                handler = logging.StreamHandler(sys.stderr)
                handler.setLevel(level)
                handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
                storage_logger.addHandler(handler)
            storage_logger.propagate = False
        else:
            # Low verbosity: suppress INFO+ messages from storage modules
            storage_logger.setLevel(logging.WARNING)
            # Remove any console handlers we (or LOGGING config) attached
            for h in console_handlers:
                storage_logger.removeHandler(h)
            storage_logger.propagate = True

    def handle(self, *args, **options):
        cluster_arg = options.get("cluster")
        dry_run = options.get("dry_run", False)
        verbosity = options.get("verbosity", 1)

        self._configure_storage_logging(verbosity)

        # Resolve cluster to a name
        cluster_names: list[str] | None = None
        if cluster_arg is not None:
            try:
                cluster_id = int(cluster_arg)
                cluster = StorageCluster.objects.get(pk=cluster_id)
            except ValueError:
                try:
                    cluster = StorageCluster.objects.get(name=cluster_arg)
                except StorageCluster.DoesNotExist:
                    self.stderr.write(self.style.ERROR(f"Cluster '{cluster_arg}' not found"))
                    return
            except StorageCluster.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Cluster '{cluster_arg}' not found"))
                return
            cluster_names = [cluster.name]

        start = timezone.now()
        if dry_run:
            self.stdout.write(self.style.NOTICE("Dry-run mode — no backend calls will be made"))
            self.stdout.write(
                self.style.NOTICE(
                    "Starting Storage sync" + ("" if cluster_names is None else f" (cluster={cluster_names[0]})")
                )
            )
            reports = self._run_sync(cluster_names, dry_run=True)
        else:
            self.stdout.write(
                self.style.NOTICE(
                    "Starting Storage sync" + ("" if cluster_names is None else f" (cluster={cluster_names[0]})")
                )
            )
            reports = self._run_sync(cluster_names)

        duration = timedelta(seconds=(timezone.now() - start).total_seconds())
        for r in reports:
            if r.success:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[OK] {r.cluster}: "
                        f"{r.paths_created} paths, "
                        f"{r.quotas_created} quotas created; "
                        f"{r.quotas_updated} quotas updated; "
                        f"{r.paths_locked} paths locked, "
                        f"{r.paths_unlocked} paths unlocked; "
                        f"{r.quotas_deleted} quotas deleted; "
                        f"{r.usage_updated} usage rows updated "
                        f"({r.duration_ms} ms)"
                    )
                )
            else:
                self.stdout.write(self.style.ERROR(f"[FAIL] {r.cluster}: {'; '.join(r.errors)}"))
            for w in r.warnings:
                self.stdout.write(self.style.WARNING(f"  warn: {w}"))

        ok = sum(1 for r in reports if r.success)
        total = len(reports)
        self.stdout.write(self.style.SUCCESS(f"Sync finished: {ok}/{total} clusters OK ({duration})"))

    def _run_sync(self, cluster_names: list[str] | None, dry_run: bool = False):
        from coldfront.storage.sync import sync_storage_clusters

        return sync_storage_clusters(cluster_names, dry_run=dry_run)
