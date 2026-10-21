# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import croniter
from django.core.exceptions import ImproperlyConfigured

from coldfront.lib.registry import registry

__all__ = (
    "system_job",
    "system_jobs",
)

#: Convenience alias for the system_jobs registry store.
system_jobs = registry.setdefault("system_jobs", {})


def system_job(*, interval=None, cron_schedule=None):
    """
    Decorator for registering a `JobRunner` subclass as a system background job.

    System jobs are periodic tasks that ColdFront itself registers (e.g., Slurm sync,
    notification digest, cleanup). They are scheduled once at worker startup via
    ``enqueue_once()``, and the ``finally`` block in ``JobRunner.handle()`` reschedules
    each iteration after completion.

    Exactly one of ``interval`` or ``cron_schedule`` must be provided.

    Args:
        interval: Recurrence interval in minutes (must be a positive integer).
        cron_schedule: A cron expression (e.g. ``"0 9 * * *"``) evaluated in the
            default timezone (Django's ``TIME_ZONE``). Missed occurrences are
            skipped; the next run is the first occurrence after the current time.

    Example::

        @system_job(interval=15)
        class SlurmSyncJob(JobRunner):
            def run(self, cluster_id=None): ...


        @system_job(cron_schedule="0 9 * * *")
        class SlurmSyncJob(JobRunner):
            def run(self, cluster_id=None): ...
    """
    if interval is None and cron_schedule is None:
        raise ImproperlyConfigured("System job requires an interval (minutes) or a cron_schedule.")
    if interval is not None and cron_schedule is not None:
        raise ImproperlyConfigured("System job cannot have both an interval and a cron_schedule.")

    if interval is not None:
        if type(interval) is not int:
            raise ImproperlyConfigured("System job interval must be an integer (minutes).")
        if interval <= 0:
            raise ImproperlyConfigured("System job interval must be a positive integer (minutes).")

    if cron_schedule is not None:
        try:
            croniter.croniter(cron_schedule)
        except (ValueError, KeyError) as e:
            raise ImproperlyConfigured(f"System job has an invalid cron_schedule ({cron_schedule}): {e}") from e

    def _wrapper(cls):
        config = {}
        if interval is not None:
            config["interval"] = interval
        if cron_schedule is not None:
            config["cron_schedule"] = cron_schedule
        system_jobs[cls] = config
        return cls

    return _wrapper
