# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import uuid
from datetime import timedelta

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from coldfront.core.choices import JobStatusChoices
from coldfront.core.models import Job


def _create_job(status, completed_days_ago, queue_name="default"):
    """Helper to create a Job with a specific status and completion time."""
    return Job.objects.create(
        name="Prune Test",
        job_id=uuid.uuid4(),
        status=status,
        completed=timezone.now() - timedelta(days=completed_days_ago),
        queue_name=queue_name,
    )


class PruneTasksCommandTestCase(TestCase):
    def setUp(self):
        super().setUp()
        # Create jobs of varying ages and statuses
        # Completed
        _create_job(JobStatusChoices.STATUS_COMPLETED, 10)  # recent
        _create_job(JobStatusChoices.STATUS_COMPLETED, 100)  # old
        _create_job(JobStatusChoices.STATUS_COMPLETED, 200)  # very old
        # Failed
        _create_job(JobStatusChoices.STATUS_FAILED, 10)
        _create_job(JobStatusChoices.STATUS_FAILED, 100)
        # Errored
        _create_job(JobStatusChoices.STATUS_ERRORED, 10)
        # Running (should never be pruned)
        _create_job(JobStatusChoices.STATUS_RUNNING, 200)
        # Pending (should never be pruned)
        _create_job(JobStatusChoices.STATUS_PENDING, 200)

    def test_prunes_old_completed_default_retention(self):
        """Default 90-day retention prunes completed > 90 days."""
        call_command("prune_tasks", verbosity=0)
        remaining = Job.objects.count()
        # 8 created - 2 old completed (100, 200) - 1 old failed (100) = 5
        self.assertEqual(remaining, 5)

    @override_settings(JOB_COMPLETED_RETENTION=-1, JOB_FAILED_RETENTION=-1)
    def test_disabled_retention_skips_all(self):
        """When retention is negative, nothing is pruned."""
        call_command("prune_tasks", verbosity=0)
        self.assertEqual(Job.objects.count(), 8)

    @override_settings(JOB_COMPLETED_RETENTION=200)
    def test_extended_completed_retention(self):
        """With 200-day completed retention, failed/errored > 90 are pruned
        (JOB_FAILED_RETENTION still defaults to 90)."""
        call_command("prune_tasks", verbosity=0)
        remaining = Job.objects.count()
        # 8 - 1 old failed (100) - 1 old completed (200) = 6
        # (completed 200-day-old is right at the 200-day boundary and gets pruned)
        self.assertEqual(remaining, 6)

    @override_settings(JOB_FAILED_RETENTION=50)
    def test_separate_failed_retention(self):
        """Failed retention can differ from completed retention."""
        call_command("prune_tasks", verbosity=0)
        remaining = Job.objects.count()
        # 8 - 2 old completed (100, 200) - 1 old failed (100) - 0 errored = 5
        self.assertEqual(remaining, 5)

    def test_queue_filter(self):
        """--queue-name filters which queues to prune."""
        # Add a job on a different queue
        _create_job(JobStatusChoices.STATUS_COMPLETED, 200, queue_name="other_queue")

        call_command("prune_tasks", queue_name="default", verbosity=0)
        remaining = Job.objects.count()
        # 9 total - 2 old completed (100, 200) on 'default' - 1 old failed (100) = 6
        # The 'other_queue' job (200 days old) is NOT pruned because queue doesn't match
        self.assertEqual(remaining, 6)

    def test_dry_run_does_not_delete(self):
        """--dry-run shows count without deleting."""
        import logging

        logger = logging.getLogger("coldfront.prune_tasks")
        with self.assertLogs(logger, level="INFO") as log:
            call_command("prune_tasks", dry_run=True, verbosity=1)
        self.assertEqual(Job.objects.count(), 8)
        self.assertIn("Would delete", log.output[0])

    def test_cli_overrides_settings(self):
        """--min-age-days CLI arg overrides JOB_COMPLETED_RETENTION."""
        call_command("prune_tasks", min_age_days=50, verbosity=0)
        remaining = Job.objects.count()
        # 8 - 2 old completed (100, 200) - 1 old failed (100) = 5
        self.assertEqual(remaining, 5)

    def test_never_prunes_running_or_pending(self):
        """Running and pending jobs are never pruned regardless of age."""
        call_command("prune_tasks", min_age_days=0, verbosity=0)
        # With min_age_days=0, completed retention = 0 → all 3 completed pruned.
        # Failed retention still defaults to JOB_FAILED_RETENTION=90 → only
        # the 100-day-old failed job is pruned.  The 10-day-old failed and
        # 10-day-old errored are kept.
        remaining = Job.objects.count()
        # 8 - 3 completed - 1 failed = 4 (running + pending + failed 10 + errored 10)
        self.assertEqual(remaining, 4)
