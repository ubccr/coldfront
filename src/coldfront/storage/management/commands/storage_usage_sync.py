# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Management command to sync quota usage from storage system backends.

Usage::

    coldfront storage_usage_sync                    # sync all clusters
    coldfront storage_usage_sync --cluster 3        # sync a single cluster by pk
    coldfront storage_usage_sync --cluster hpc01    # sync a single cluster by name

This command runs synchronously and calls the same reconciliation code
path (``sync_storage_usage``) as the system jobs.  It never mutates the
backend — it only pulls usage into the active quota rows and recalculates
resource/cluster used-bytes sums.
"""

import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from coldfront.storage.models import StorageCluster

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Sync quota usage from storage backends into ColdFront"

    def add_arguments(self, parser):
        parser.add_argument(
            "--cluster",
            help="Cluster PK or name. Syncs all clusters when omitted.",
        )

    def handle(self, *args, **options):
        cluster_arg = options.get("cluster")

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
        self.stdout.write(
            self.style.NOTICE(
                "Starting Storage usage sync" + ("" if cluster_names is None else f" (cluster={cluster_names[0]})")
            )
        )

        from coldfront.storage.sync import sync_storage_usage

        reports = sync_storage_usage(cluster_names)

        duration = timedelta(seconds=(timezone.now() - start).total_seconds())
        for r in reports:
            if r.success:
                self.stdout.write(
                    self.style.SUCCESS(f"[OK] {r.cluster}: {r.usage_updated} usage rows updated ({r.duration_ms} ms)")
                )
            else:
                self.stdout.write(self.style.ERROR(f"[FAIL] {r.cluster}: {'; '.join(r.errors)}"))
            for w in r.warnings:
                self.stdout.write(self.style.WARNING(f"  warn: {w}"))

        ok = sum(1 for r in reports if r.success)
        total = len(reports)
        self.stdout.write(self.style.SUCCESS(f"Usage sync finished: {ok}/{total} clusters OK ({duration})"))
