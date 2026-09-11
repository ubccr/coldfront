# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Management command to synchronize ColdFront Slurm models with slurmrestd.

Usage::

    coldfront slurm_sync                          # sync all clusters
    coldfront slurm_sync --cluster 3              # sync a single cluster by pk
    coldfront slurm_sync --cluster hpc01          # sync a single cluster by name
    coldfront slurm_sync --dry-run                # show what would change
    coldfront slurm_sync --cluster hpc01 --dry-run

This command always runs synchronously. It skips clusters without slurmrestd
configured — unconfigured clusters are reported as failures."""

import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from coldfront.slurm.models import SlurmCluster

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Synchronize ColdFront Slurm models with slurmrestd"

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

    def handle(self, *args, **options):
        cluster_arg = options.get("cluster")
        dry_run = options.get("dry_run", False)

        # Resolve cluster to a name
        cluster_names: list[str] | None = None
        if cluster_arg is not None:
            try:
                cluster_id = int(cluster_arg)
                cluster = SlurmCluster.objects.get(pk=cluster_id)
            except ValueError:
                try:
                    cluster = SlurmCluster.objects.get(name=cluster_arg)
                except SlurmCluster.DoesNotExist:
                    self.stderr.write(self.style.ERROR(f"Cluster '{cluster_arg}' not found"))
                    return
            except SlurmCluster.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Cluster '{cluster_arg}' not found"))
                return
            cluster_names = [cluster.name]

        if dry_run:
            self._dry_run(cluster_names)
        else:
            self._run_sync(cluster_names)

    def _run_sync(self, cluster_names: list[str] | None) -> None:
        from coldfront.slurm.sync import sync_slurm_clusters

        start = timezone.now()
        self.stdout.write(
            self.style.NOTICE(
                "Starting Slurm sync" + ("" if cluster_names is None else f" (cluster={cluster_names[0]})")
            )
        )

        reports = sync_slurm_clusters(cluster_names)

        duration = timedelta(seconds=(timezone.now() - start).total_seconds())
        for r in reports:
            if r.success:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[OK] {r.cluster}: "
                        f"{r.accounts_created} accounts, "
                        f"{r.associations_created} assocs, "
                        f"{r.users_created} users created; "
                        f"{r.associations_deleted} assocs, "
                        f"{r.users_deleted} users, "
                        f"{r.accounts_deleted} accounts, "
                        f"{r.qos_deleted} QOS deleted; "
                        f"{r.jobs_killed} jobs killed "
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

    def _dry_run(self, cluster_names: list[str] | None) -> None:
        """Show what would change without making API calls."""
        self.stdout.write(self.style.NOTICE("Dry-run mode — no API calls will be made"))

        clusters = SlurmCluster.objects.all()
        if cluster_names is not None:
            clusters = clusters.filter(name__in=cluster_names)

        from coldfront.slurm.export.associations import _get_accounts_for_assocs
        from coldfront.slurm.utils import get_active_associations

        for cluster in clusters:
            self.stdout.write(f"\nCluster: {cluster.name}")
            active = get_active_associations(cluster)
            self.stdout.write(f"  Active associations: {len(active)}")

            accounts = _get_accounts_for_assocs(active)
            self.stdout.write(f"  Unique accounts: {len(accounts)}")

            # Count unique users
            user_set: set[str] = set()
            for a in active:
                allocation = a.allocation
                if allocation and allocation.project:
                    for pu in allocation.project.users.all():
                        if pu.user:
                            user_set.add(pu.user.username)
            self.stdout.write(f"  Unique users: {len(user_set)}")

            if active:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  Would upsert: {len(accounts)} accounts, {len(active)} associations, {len(user_set)} users"
                    )
                )
            else:
                self.stdout.write(self.style.WARNING("  No active associations — nothing to upsert"))
