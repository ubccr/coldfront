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

This command always runs synchronously and is unaffected by the
per-cluster ``auto_sync_enabled`` setting — it bypasses the auto-sync
gate entirely.
"""

from __future__ import annotations

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

        # Resolve cluster
        cluster_id: int | None = None
        if cluster_arg is not None:
            try:
                cluster_id = int(cluster_arg)
            except ValueError:
                # Look up by name
                try:
                    cluster = StorageCluster.objects.get(name=cluster_arg)
                    cluster_id = cluster.pk
                except StorageCluster.DoesNotExist:
                    self.stderr.write(self.style.ERROR(f"Cluster '{cluster_arg}' not found"))
                    return

        if dry_run:
            self._dry_run(cluster_id)
        else:
            self._run_sync(cluster_id)

    def _run_sync(self, cluster_id: int | None) -> None:
        from coldfront.storage.sync import run_sync

        start = timezone.now()
        if cluster_id is None:
            self.stdout.write(self.style.NOTICE("Starting Storage sync"))
        else:
            self.stdout.write(self.style.NOTICE("Starting Storage sync (cluster=%s)", cluster_id))

        reports = run_sync(cluster_id=cluster_id)

        duration = timedelta(seconds=(timezone.now() - start).total_seconds())
        for r in reports:
            if r.success:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[OK] {r.cluster}: "
                        f"{r.paths_created} paths, "
                        f"{r.quotas_created} quotas created; "
                        f"{r.quotas_updated} quotas updated; "
                        f"{r.paths_deleted} paths, "
                        f"{r.quotas_deleted} quotas deleted "
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

    def _dry_run(self, cluster_id: int | None) -> None:
        """Show what would change without making API calls."""
        self.stdout.write(self.style.NOTICE("Dry-run mode — no API calls will be made"))

        clusters = StorageCluster.objects.all()
        if cluster_id is not None:
            clusters = clusters.filter(pk=cluster_id)

        from coldfront.ras.choices import AllocationStatusChoices
        from coldfront.storage.models import StorageQuota

        for cluster in clusters:
            self.stdout.write(f"\nCluster: {cluster.name}")

            # Count active quotas that apply to this cluster
            active_quotas = StorageQuota.objects.filter(
                allocation__status=AllocationStatusChoices.STATUS_ACTIVE,
            )

            expected_count = 0
            for quota in active_quotas:
                if quota.clusters.exists():
                    if quota.clusters.filter(pk=cluster.pk).exists():
                        expected_count += 1
                else:
                    if quota.storage.clusters.filter(pk=cluster.pk).exists():
                        expected_count += 1

            self.stdout.write(f"  Active quotas on this cluster: {expected_count}")

            if expected_count:
                self.stdout.write(self.style.SUCCESS(f"  Would create/update: {expected_count} quotas"))
            else:
                self.stdout.write(self.style.WARNING("  No active quotas — nothing to sync"))
