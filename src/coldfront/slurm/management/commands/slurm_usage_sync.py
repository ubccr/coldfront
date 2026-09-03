# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Management command to ingest daily SU usage from slurmrestd.

Usage::

    coldfront slurm_usage_sync                          # sync all clusters (capped catch-up)
    coldfront slurm_usage_sync --cluster hpc01          # sync a single cluster by name/pk
    coldfront slurm_usage_sync --start 2024-01-01 --end 2024-01-10
    coldfront slurm_usage_sync --cluster hpc01 --start 2024-01-01 --end 2024-01-10

This command runs synchronously and bypasses the per-cluster ``auto_sync_enabled``
gate — it is the admin re-ingest / repair path.
"""

from __future__ import annotations

import logging
from datetime import date

from django.core.management.base import BaseCommand

from coldfront.slurm.models import SlurmCluster

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Ingest daily per-account SU usage from slurmrestd"

    def add_arguments(self, parser):
        parser.add_argument(
            "--cluster",
            help="Cluster PK or name. Syncs all clusters when omitted.",
        )
        parser.add_argument(
            "--start",
            help="Start day (YYYY-MM-DD, inclusive). Defaults to the capped catch-up range.",
        )
        parser.add_argument(
            "--end",
            help="End day (YYYY-MM-DD, inclusive). Defaults to yesterday.",
        )

    def handle(self, *args, **options):
        cluster_arg = options.get("cluster")
        start_arg = options.get("start")
        end_arg = options.get("end")

        # Resolve cluster
        cluster_id: int | None = None
        if cluster_arg is not None:
            try:
                cluster_id = int(cluster_arg)
            except ValueError:
                try:
                    cluster = SlurmCluster.objects.get(name=cluster_arg)
                    cluster_id = cluster.pk
                except SlurmCluster.DoesNotExist:
                    self.stderr.write(self.style.ERROR(f"Cluster '{cluster_arg}' not found"))
                    return

        from coldfront.slurm.sync import _resolve_catchup_range, _run_usage_sync

        clusters = SlurmCluster.objects.all()
        if cluster_id is not None:
            clusters = clusters.filter(pk=cluster_id)

        for cluster in clusters:
            if start_arg and end_arg:
                try:
                    start_day = date.fromisoformat(start_arg)
                    end_day = date.fromisoformat(end_arg)
                except ValueError as exc:
                    self.stderr.write(self.style.ERROR(f"Invalid date: {exc}"))
                    return
            else:
                rng = _resolve_catchup_range(cluster)
                if rng is None:
                    self.stdout.write(
                        self.style.NOTICE(f"[SKIP] {cluster.name}: no days to sync (last={cluster.last_usage_sync})")
                    )
                    continue
                start_day, end_day = rng

            self.stdout.write(self.style.NOTICE(f"Starting usage sync for {cluster.name}: [{start_day} .. {end_day}]"))
            report = _run_usage_sync(cluster, start_day, end_day)
            if report.success:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[OK] {cluster.name}: {report.days_synced} days, "
                        f"{report.accounts_updated} accounts, "
                        f"{report.jobs_ingested} jobs ({report.duration_ms} ms)"
                    )
                )
            else:
                self.stdout.write(self.style.ERROR(f"[FAIL] {cluster.name}: {'; '.join(report.errors)}"))
            for w in report.warnings:
                self.stdout.write(self.style.WARNING(f"  warn: {w}"))
