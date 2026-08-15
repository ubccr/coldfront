# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import logging
import os
import traceback
from abc import ABC, abstractmethod
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path

from django.utils import timezone
from django.utils.functional import classproperty
from rq.timeouts import JobTimeoutException

from coldfront.core.choices import JobStatusChoices
from coldfront.core.exceptions import JobFailed
from coldfront.core.jobs.registry import system_jobs
from coldfront.core.models import Job
from coldfront.core.models.object_types import ObjectType

__all__ = (
    "JobLogHandler",
    "JobRunner",
)

# The installation root, e.g. "/opt/coldfront/". Used to strip absolute path
# prefixes from traceback file paths before recording them in the job log.
# runner.py lives at <root>/coldfront/core/jobs/runner.py, so parents[3] is the root.
_INSTALL_ROOT = str(Path(__file__).resolve().parents[3]) + os.sep


class JobLogHandler(logging.Handler):
    """
    A logging handler which records entries on a Job's log_entries field.
    """

    def __init__(self, job, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.job = job

    def emit(self, record):
        self.job.log(record)


class JobRunner(ABC):
    """
    Background Job helper class.

    This class handles the execution of a background job. It is responsible for
    maintaining its state, reporting errors, and scheduling recurring jobs.
    """

    class Meta:
        pass

    def __init__(self, job):
        self.job = job

        # Initiate the system logger
        self.logger = logging.getLogger(f"coldfront.jobs.{self.__class__.__name__}")
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(JobLogHandler(job))

    @classmethod
    @contextmanager
    def _redis_lock(cls, key, timeout=30):
        """
        Acquire a Redis-based lock for the given key.

        Uses the default RQ queue's Redis connection so no extra infrastructure
        is needed. Works with any database backend (SQLite, MySQL, PostgreSQL).

        Falls back to a no-op context manager if Redis is unavailable, so callers
        can use this in development without a running Redis server.
        """
        try:
            from django_rq.connection_utils import get_connection

            conn = get_connection("default")
            lock = conn.lock(key, timeout=timeout, blocking_timeout=timeout)
            with lock:
                yield
        except Exception:
            # Redis not available; proceed without locking.
            yield

    @classproperty
    def name(cls):
        return getattr(cls.Meta, "name", cls.__name__)

    @abstractmethod
    def run(self, *args, **kwargs):
        """
        Run the job.

        A `JobRunner` subclass needs to implement this method to execute all commands of the job.
        """
        pass

    @classmethod
    def handle(cls, job, *args, **kwargs):
        """
        Handle the execution of a `Job`.

        This method is called by the job scheduler to handle the execution of all job commands.
        It will maintain the job's metadata and handle errors. For periodic jobs, a new job is
        automatically scheduled using its `interval`.
        """
        logger = logging.getLogger("coldfront.jobs")

        try:
            job.start()
            cls(job).run(*args, **kwargs)
            job.terminate()

        except JobFailed:
            logger.warning(f"Job {job} failed")
            job.terminate(status=JobStatusChoices.STATUS_FAILED)

        except Exception as e:
            tb_str = traceback.format_exc().replace(_INSTALL_ROOT, "")
            tb_record = logging.makeLogRecord(
                {
                    "levelno": logging.ERROR,
                    "levelname": "ERROR",
                    "msg": tb_str,
                }
            )
            job.log(tb_record)
            job.terminate(status=JobStatusChoices.STATUS_ERRORED, error=repr(e))
            if type(e) is JobTimeoutException:
                logger.error(e)

        # If the executed job is a periodic job, schedule its next execution at the specified interval.
        finally:
            if job.interval:
                # Determine the new scheduled time. Cannot be earlier than one minute in the future.
                new_scheduled_time = max(
                    (job.scheduled or job.started) + timedelta(minutes=job.interval),
                    timezone.now() + timedelta(minutes=1),
                )

                enqueue_kwargs = dict(
                    instance=job.object,
                    name=job.name,
                    user=job.user,
                    schedule_at=new_scheduled_time,
                    interval=job.interval,
                    notifications=job.notifications,
                    **kwargs,
                )

                if cls in system_jobs:
                    # System jobs are also scheduled by `enqueue_once()` at worker startup,
                    # which races with this finally block and can produce duplicate schedules.
                    # Acquire the same Redis lock used by `enqueue_once()` and skip
                    # rescheduling if a successor is already enqueued.
                    #
                    # This branch is limited to system jobs because generic recurring jobs
                    # (e.g., scheduled scripts) may have multiple legitimate schedules sharing
                    # the same runner/object/interval but differing in their runtime kwargs.
                    from coldfront.constants import LOCK_KEYS

                    with cls._redis_lock(LOCK_KEYS["job-schedules"]):
                        successor_exists = (
                            Job.objects.filter(
                                name=cls.name,
                                object_id__isnull=True,
                                status__in=JobStatusChoices.ENQUEUED_STATE_CHOICES,
                                interval=job.interval,
                            )
                            .exclude(pk=job.pk)
                            .exists()
                        )
                        if not successor_exists:
                            cls.enqueue(**enqueue_kwargs)
                else:
                    cls.enqueue(**enqueue_kwargs)

    @classmethod
    def get_jobs(cls, instance=None):
        """
        Get all jobs of this `JobRunner` related to a specific instance.
        """
        jobs = Job.objects.filter(name=cls.name)

        if instance:
            object_type = ObjectType.objects.get_for_model(instance, for_concrete_model=False)
            jobs = jobs.filter(
                object_type=object_type,
                object_id=instance.pk,
            )

        return jobs

    @classmethod
    def enqueue(cls, *args, **kwargs):
        """
        Enqueue a new `Job`.

        This method is a wrapper of ``Job.enqueue()`` using ``handle()`` as function
        callback. See its documentation for parameters.
        """
        name = kwargs.pop("name", None) or cls.name
        return Job.enqueue(cls.handle, name=name, *args, **kwargs)

    @classmethod
    def enqueue_once(cls, instance=None, schedule_at=None, interval=None, *args, **kwargs):
        """
        Enqueue a new `Job` once, i.e. skip duplicate jobs.

        Like ``enqueue()``, this method adds a new `Job` to the job queue. However, if
        there's already a job of this class scheduled for ``instance``, the existing job
        will be updated if necessary. This ensures that a particular schedule is only set
        up once at any given time — i.e., multiple calls to this method are idempotent.

        Note that this does not forbid running additional jobs with the ``enqueue()``
        method, e.g. to schedule an immediate synchronization job in addition to a
        periodic synchronization schedule.

        For additional parameters see ``enqueue()``.

        Args:
            instance: The ColdFront object to which this job pertains (optional)
            schedule_at: Schedule the job to be executed at the passed date and time
            interval: Recurrence interval (in minutes)
        """
        from coldfront.constants import LOCK_KEYS

        with cls._redis_lock(LOCK_KEYS["job-schedules"]):
            job = (
                cls.get_jobs(instance)
                .filter(
                    status__in=JobStatusChoices.ENQUEUED_STATE_CHOICES,
                )
                .first()
            )
            if job:
                # If the job parameters haven't changed, don't schedule a new job and keep
                # the current schedule. Otherwise, delete the existing job and schedule a
                # new job instead.
                if (not schedule_at or job.scheduled == schedule_at) and (job.interval == interval):
                    return job
                job.delete()

            return cls.enqueue(
                instance=instance,
                schedule_at=schedule_at,
                interval=interval,
                *args,
                **kwargs,
            )
