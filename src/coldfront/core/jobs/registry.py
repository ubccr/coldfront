# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.core.exceptions import ImproperlyConfigured

from coldfront.registry import registry

__all__ = (
    "system_job",
    "system_jobs",
)

#: Convenience alias for the system_jobs registry store.
system_jobs = registry.setdefault("system_jobs", {})


def system_job(interval):
    """
    Decorator for registering a `JobRunner` subclass as a system background job.

    System jobs are periodic tasks that ColdFront itself registers (e.g., Slurm sync,
    notification digest, cleanup). They are scheduled once at worker startup via
    ``enqueue_once()``, and the ``finally`` block in ``JobRunner.handle()`` reschedules
    each iteration after completion.

    Args:
        interval: Recurrence interval in minutes (must be a positive integer).

    Example::

        @system_job(interval=15)
        class SlurmSyncJob(JobRunner):
            def run(self, cluster_id=None): ...
    """
    if type(interval) is not int:
        raise ImproperlyConfigured("System job interval must be an integer (minutes).")
    if interval <= 0:
        raise ImproperlyConfigured("System job interval must be a positive integer (minutes).")

    def _wrapper(cls):
        system_jobs[cls] = {
            "interval": interval,
        }
        return cls

    return _wrapper
