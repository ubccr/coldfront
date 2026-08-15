# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from coldfront.core.choices import JobStatusChoices
from coldfront.core.jobs.registry import system_job
from coldfront.core.jobs.runner import JobRunner
from coldfront.core.models import Job, ObjectChange

__all__ = (
    "PruneChangeLogJob",
    "NotificationDigestJob",
    "PruneJob",
)


@system_job(interval=1440)  # daily
class PruneChangeLogJob(JobRunner):
    """
    System job that removes stale ObjectChange records older than
    ``settings.CHANGELOG_RETENTION`` days.  If the retention period is
    zero (or negative), the job skips deletion entirely.
    """

    class Meta:
        name = "coldfront.core.tasks.system.PruneChangeLogJob"

    def run(self, *_args, **_kwargs):
        retention = getattr(settings, "CHANGELOG_RETENTION", 90)
        if retention <= 0:
            self.logger.info("CHANGELOG_RETENTION=%s, skipping cleanup", retention)
            return

        cutoff = timezone.now() - timedelta(days=retention)
        deleted, _ = ObjectChange.objects.filter(time__lt=cutoff).delete()
        self.logger.info(
            "Deleted %s ObjectChange records older than %s days",
            deleted,
            retention,
        )


@system_job(interval=1440)  # daily
class PruneJob(JobRunner):
    """
    System job that removes stale Job records according to retention settings.

    * ``JOB_COMPLETED_RETENTION`` — completed jobs older than this many days
      are deleted (default: 90).
    * ``JOB_FAILED_RETENTION`` — failed/errored jobs older than this many days
      are deleted (default: 90).

    If a retention value is zero or negative, jobs of that status are kept
    indefinitely.
    """

    class Meta:
        name = "coldfront.core.tasks.system.PruneJob"

    def run(self, *_args, **_kwargs):
        completed_retention = getattr(settings, "JOB_COMPLETED_RETENTION", 90)
        failed_retention = getattr(settings, "JOB_FAILED_RETENTION", completed_retention)

        if completed_retention <= 0 and failed_retention <= 0:
            self.logger.info(
                "Retention disabled (completed=%s, failed=%s), skipping",
                completed_retention,
                failed_retention,
            )
            return

        now = timezone.now()
        total_deleted = 0

        # Prune completed jobs
        if completed_retention > 0:
            cutoff = now - timedelta(days=completed_retention)
            deleted, _ = (
                Job.objects.finished()
                .filter(
                    status=JobStatusChoices.STATUS_COMPLETED,
                    completed__lte=cutoff,
                )
                .delete()
            )
            total_deleted += deleted
            self.logger.info(
                "Deleted %s completed Job records older than %s days",
                deleted,
                completed_retention,
            )
        else:
            self.logger.info(
                "JOB_COMPLETED_RETENTION=%s, skipping completed jobs",
                completed_retention,
            )

        # Prune failed / errored jobs
        if failed_retention > 0:
            cutoff = now - timedelta(days=failed_retention)
            deleted, _ = (
                Job.objects.finished()
                .filter(
                    status__in=[
                        JobStatusChoices.STATUS_FAILED,
                        JobStatusChoices.STATUS_ERRORED,
                    ],
                    completed__lte=cutoff,
                )
                .delete()
            )
            total_deleted += deleted
            self.logger.info(
                "Deleted %s failed/errored Job records older than %s days",
                deleted,
                failed_retention,
            )
        else:
            self.logger.info(
                "JOB_FAILED_RETENTION=%s, skipping failed jobs",
                failed_retention,
            )

        self.logger.info(
            "PruneJob finished: deleted %s total Job records",
            total_deleted,
        )


@system_job(interval=1440)  # daily
class NotificationDigestJob(JobRunner):
    """
    System job that sends daily notification digests via
    ``send_notification_digests()``.
    """

    class Meta:
        name = "coldfront.core.tasks.system.NotificationDigestJob"

    def run(self, *_args, **_kwargs):
        from generic_notifications.digest import send_notification_digests
        from generic_notifications.frequencies import DailyFrequency

        sent = send_notification_digests(DailyFrequency)
        self.logger.info("Sent %s daily notification digests", sent)
