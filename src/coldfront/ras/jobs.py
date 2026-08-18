# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from coldfront.core.jobs.registry import system_job
from coldfront.core.jobs.runner import JobRunner
from coldfront.ras.models import ProjectInvite


@system_job(interval=1440)  # daily
class PruneProjectInviteJob(JobRunner):
    """
    Deletes expired and accepted project invites.

    Expiration is computed (never stored) from ``created`` plus
    ``INVITE_CODE_EXPIRE_SECONDS``; the accept view independently rejects
    expired invites, so this job is hygiene cleanup.

    Expired invites are always deleted. Accepted invites are only deleted when
    their ``accepted_at`` timestamp is older than
    ``settings.ACCEPTED_INVITE_RETENTION`` days. If the retention period is zero
    (or negative), accepted invites are kept indefinitely.
    """

    class Meta:
        name = "coldfront.ras.jobs.ProjectInviteExpirationJob"

    def run(self, *_args, **_kwargs):
        # Expired invites are always deleted, regardless of retention.
        expired = ProjectInvite.objects.expired()
        expired_count = expired.count()
        expired.delete()
        self.logger.info("Deleted %s expired invites", expired_count)

        # Accepted invites are only deleted once they are older than the
        # retention period (measured from their accepted_at timestamp).
        retention = getattr(settings, "ACCEPTED_INVITE_RETENTION", 90)
        if retention > 0:
            cutoff = timezone.now() - timedelta(days=retention)
            accepted_old = ProjectInvite.objects.accepted().filter(accepted_at__lt=cutoff)
            accepted_count = accepted_old.count()
            accepted_old.delete()
            self.logger.info(
                "Deleted %s accepted invites older than %s days",
                accepted_count,
                retention,
            )
        else:
            self.logger.info(
                "ACCEPTED_INVITE_RETENTION=%s, skipping accepted invite cleanup",
                retention,
            )

        return True
