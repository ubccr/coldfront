# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import inspect
import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime

import django_rq
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import SuspiciousOperation, ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.tasks import Task
from django.urls import reverse
from django.utils import timezone
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _
from django_tasks.base import (
    DEFAULT_TASK_PRIORITY,
    TaskError,
    TaskResultStatus,
)
from django_tasks.base import (
    TaskResult as TaskResultBase,
)
from django_tasks.utils import get_exception_traceback, get_module_path
from rq.exceptions import InvalidJobOperation

from coldfront.core.choices import JobNotificationChoices, JobStatusChoices
from coldfront.core.events import JOB_COMPLETED, JOB_ERRORED, JOB_FAILED
from coldfront.core.models.object_types import ObjectType
from coldfront.core.utils import JobLogDecoder
from coldfront.users.querysets import RestrictedQuerySet

__all__ = (
    "Job",
    "JobLogEntry",
)

# Map Job statuses to django-tasks TaskResultStatus values
JOB_TO_TASK_RESULT_STATUS = {
    JobStatusChoices.STATUS_PENDING: TaskResultStatus.READY,
    JobStatusChoices.STATUS_SCHEDULED: TaskResultStatus.READY,
    JobStatusChoices.STATUS_RUNNING: TaskResultStatus.RUNNING,
    JobStatusChoices.STATUS_COMPLETED: TaskResultStatus.SUCCESSFUL,
    JobStatusChoices.STATUS_FAILED: TaskResultStatus.FAILED,
    JobStatusChoices.STATUS_ERRORED: TaskResultStatus.FAILED,
}

# Classes that are accepted as a valid task reference
try:
    from django.tasks.base import Task as DjangoTask
except ImportError:
    DjangoTask = None

TASK_CLASSES = (Task, DjangoTask) if DjangoTask is not None else (Task,)


@dataclass
class JobLogEntry:
    """A structured log entry attached to a Job."""

    timestamp: str
    level: str
    message: str

    @classmethod
    def from_logrecord(cls, record: logging.LogRecord):
        return cls(
            timestamp=datetime.fromtimestamp(record.created).isoformat(),
            level=record.levelname,
            message=record.getMessage(),
        )


class JobQuerySet(RestrictedQuerySet):
    """Custom queryset for Job with worker queue methods."""

    def ready(self):
        """
        Return jobs that are ready to be processed by a worker.

        A job is ready when its status is PENDING or SCHEDULED and its
        scheduled time (if set) has passed.
        """
        return self.filter(
            status__in=[JobStatusChoices.STATUS_PENDING, JobStatusChoices.STATUS_SCHEDULED],
        ).filter(
            Q(scheduled__isnull=True) | Q(scheduled__lte=timezone.now()),
        )

    def get_locked(self):
        """
        Get a ready job, locking the row for exclusive worker access.

        Uses ``select_for_update(skip_locked=True)`` to avoid contention.
        Returns ``None`` if no ready job is available.
        """
        return self.ready().select_for_update(skip_locked=True).first()

    def finished(self):
        """
        Return jobs that have reached a terminal state (completed, failed,
        or errored).
        """
        return self.filter(status__in=JobStatusChoices.TERMINAL_STATE_CHOICES)


class Job(models.Model):
    """
    Tracks the lifecycle of a job which represents a background task.

    In addition to persistence and UI visibility, this model serves as the
    queue entry for the DB-based task backend (``ColdFrontBackend`` when
    ``COLDFRONT_TASKS_BACKEND`` points to the DB backend). Fields like
    ``task_path`` and ``args_kwargs`` store the task definition so a worker
    can reconstruct and execute the ``Task`` at the right time.
    """

    object_type = models.ForeignKey(
        to=ContentType,
        related_name="jobs",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    object_id = models.PositiveBigIntegerField(
        blank=True,
        null=True,
    )
    object = GenericForeignKey(
        ct_field="object_type",
        fk_field="object_id",
        for_concrete_model=False,
    )
    name = models.CharField(
        verbose_name=_("name"),
        max_length=200,
    )
    created = models.DateTimeField(
        verbose_name=_("created"),
        auto_now_add=True,
    )
    scheduled = models.DateTimeField(
        verbose_name=_("scheduled"),
        null=True,
        blank=True,
    )
    interval = models.PositiveIntegerField(
        verbose_name=_("interval"),
        blank=True,
        null=True,
        validators=(MinValueValidator(1),),
        help_text=_("Recurrence interval (in minutes)"),
    )
    started = models.DateTimeField(
        verbose_name=_("started"),
        null=True,
        blank=True,
    )
    completed = models.DateTimeField(
        verbose_name=_("completed"),
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="+",
        blank=True,
        null=True,
    )
    status = models.CharField(
        verbose_name=_("status"),
        max_length=30,
        choices=JobStatusChoices,
        default=JobStatusChoices.STATUS_PENDING,
    )
    data = models.JSONField(
        verbose_name=_("data"),
        encoder=DjangoJSONEncoder,
        null=True,
        blank=True,
    )
    error = models.TextField(
        verbose_name=_("error"),
        editable=False,
        blank=True,
    )
    job_id = models.UUIDField(
        verbose_name=_("job ID"),
        unique=True,
    )
    queue_name = models.CharField(
        verbose_name=_("queue name"),
        max_length=100,
        blank=True,
        help_text=_("Name of the queue in which this job was enqueued"),
    )
    notifications = models.CharField(
        verbose_name=_("notifications"),
        max_length=30,
        choices=JobNotificationChoices,
        default=JobNotificationChoices.NOTIFICATION_ALWAYS,
    )
    log_entries = models.JSONField(
        verbose_name=_("log entries"),
        encoder=DjangoJSONEncoder,
        decoder=JobLogDecoder,
        blank=True,
        default=list,
    )

    # --- Queue fields (used by the DB task backend) ---

    task_path = models.TextField(
        verbose_name=_("task path"),
        blank=True,
        help_text=_("Dotted module path of the Task function to execute"),
    )
    args_kwargs = models.JSONField(
        verbose_name=_("task arguments"),
        encoder=DjangoJSONEncoder,
        blank=True,
        default=dict,
        help_text=_("Serialized positional and keyword arguments for the task"),
    )
    priority = models.IntegerField(
        verbose_name=_("priority"),
        default=DEFAULT_TASK_PRIORITY,
        help_text=_("Queue priority (higher = sooner)"),
    )
    worker_ids = models.JSONField(
        verbose_name=_("worker IDs"),
        blank=True,
        default=list,
        help_text=_("Worker identifiers that have processed this job"),
    )

    objects = JobQuerySet.as_manager()

    class Meta:
        ordering = ["-created"]
        indexes = (
            models.Index(fields=("-created",)),  # Default ordering
            models.Index(fields=("object_type", "object_id")),
        )
        verbose_name = _("job")
        verbose_name_plural = _("jobs")

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("core:job", args=[self.pk])

    def get_status_color(self):
        return JobStatusChoices.colors.get(self.status)

    def get_event_type(self):
        return {
            JobStatusChoices.STATUS_COMPLETED: JOB_COMPLETED,
            JobStatusChoices.STATUS_FAILED: JOB_FAILED,
            JobStatusChoices.STATUS_ERRORED: JOB_ERRORED,
        }.get(self.status)

    def clean(self):
        super().clean()
        # Validate the assigned object type
        if self.object_type and not ObjectType.has_feature(self.object_type, "jobs"):
            raise ValidationError(
                _("Jobs cannot be assigned to this object type ({type}).").format(type=self.object_type)
            )

    @property
    def duration(self):
        if not self.completed:
            return None
        start_time = self.started or self.created
        if not start_time:
            return None
        duration = self.completed - start_time
        minutes, seconds = divmod(duration.total_seconds(), 60)
        return f"{int(minutes)} minutes, {seconds:.2f} seconds"

    # ------------------------------------------------------------------
    # Queue lifecycle properties and methods (DB backend)
    # ------------------------------------------------------------------

    @property
    def task(self):
        """
        Reconstruct the ``Task`` object from ``task_path``.

        ``task_path`` may point to either a ``Task`` instance (created by
        the ``@task`` decorator) or a plain function. If it is a function,
        it is wrapped in a ``Task`` object automatically.  When
        ``_runner_cls_path`` is stored in ``args_kwargs``, the path points
        to a ``JobRunner`` subclass and we use ``cls.handle.__func__`` so
        that ``validate_task`` passes (it requires a module-level callable).
        """
        if not self.task_path:
            raise SuspiciousOperation(f"Job {self.id} has no task_path; cannot reconstruct the Task.")

        obj = import_string(self.task_path)

        # If the path points to a Task instance, use it directly.
        if isinstance(obj, TASK_CLASSES):
            return obj.using(
                priority=self.priority,
                queue_name=self.queue_name or "default",
                run_after=self.scheduled,
                backend="default",
            )

        # If ``_runner_cls_path`` is stored, load the runner class and use
        # the raw ``cls.handle.__func__`` — a module-level callable that
        # passes ``validate_task``.
        runner_cls_path = self.args_kwargs.get("kwargs", {}).get("_runner_cls_path") if self.args_kwargs else None
        if runner_cls_path:
            cls = import_string(runner_cls_path)
            return Task(
                func=cls.handle.__func__,
                priority=self.priority,
                backend="default",
                queue_name=self.queue_name or "default",
                run_after=self.scheduled,
            )

        # Otherwise, wrap the callable in a Task.
        if callable(obj):
            return Task(
                func=obj,
                priority=self.priority,
                backend="default",
                queue_name=self.queue_name or "default",
                run_after=self.scheduled,
            )

        raise SuspiciousOperation(f"Job {self.id} task_path does not point to a Task or callable ({self.task_path})")

    @property
    def task_result(self):
        """
        Build a ``TaskResult`` from this Job's current state.

        The returned ``TaskResult`` reflects the live DB values (status,
        timestamps, errors, return value) at the time of the call.
        """
        errors = []
        if self.status in (JobStatusChoices.STATUS_FAILED, JobStatusChoices.STATUS_ERRORED):
            errors.append(
                TaskError(
                    exception_class_path=get_module_path(Exception),
                    traceback=self.error,
                )
            )

        result = TaskResultBase(
            task=self.task,
            id=str(self.job_id),
            status=JOB_TO_TASK_RESULT_STATUS.get(self.status, TaskResultStatus.READY),
            enqueued_at=self.created,
            started_at=self.started,
            last_attempted_at=self.started,
            finished_at=self.completed,
            args=self.args_kwargs.get("args", []) if self.args_kwargs else [],
            kwargs=self.args_kwargs.get("kwargs", {}) if self.args_kwargs else {},
            backend="default",
            errors=errors,
            worker_ids=self.worker_ids,
        )

        if self.status == JobStatusChoices.STATUS_COMPLETED:
            object.__setattr__(result, "_return_value", self.data)

        return result

    def claim(self, worker_id: str) -> None:
        """
        Mark this job as claimed by a worker for execution.

        Sets status to RUNNING, records the start time, and appends the
        worker identifier to ``worker_ids``.
        """
        self.started = timezone.now()
        self.status = JobStatusChoices.STATUS_RUNNING
        self.worker_ids = [*self.worker_ids, worker_id]
        self.save(update_fields=["started", "status", "worker_ids"])

    def set_successful(self, return_value) -> None:
        """
        Mark this job as completed successfully.

        Stores the return value in ``data`` and records the completion time.
        """
        self.status = JobStatusChoices.STATUS_COMPLETED
        self.completed = timezone.now()
        self.data = return_value
        self.error = ""
        self.save(update_fields=["status", "completed", "data", "error"])

    def set_failed(self, exc: BaseException) -> None:
        """
        Mark this job as failed due to an exception.

        Stores the exception traceback in ``error`` and clears ``data``.
        """
        self.status = JobStatusChoices.STATUS_FAILED
        self.completed = timezone.now()
        self.error = get_exception_traceback(exc)
        self.data = None
        self.save(update_fields=["status", "completed", "error", "data"])

    # ------------------------------------------------------------------
    # Original lifecycle methods
    # ------------------------------------------------------------------

    def delete(self, *args, **kwargs):
        import logging as _log

        _log.getLogger("coldfront.jobs.Job").info(
            "DEBUG delete: pk=%s status=%s name=%s", self.pk, self.status, self.name
        )
        # Cancel the RQ job before deleting the DB record
        super().delete(*args, **kwargs)

        # Best-effort cleanup of RQ job; ignore errors (e.g., Redis not running)
        try:
            rq_queue_name = self.queue_name or "default"
            queue = django_rq.get_queue(rq_queue_name)
            job = queue.fetch_job(str(self.job_id))
            if job:
                try:
                    job.cancel()
                except InvalidJobOperation:
                    pass
        except Exception:
            pass

    def start(self):
        """Record the job's start time and update its status to 'running'."""
        if self.started is not None:
            return
        self.started = timezone.now()
        self.status = JobStatusChoices.STATUS_RUNNING
        self.save()
        # Lazy import to avoid circular dependency: signals.py imports core.models
        from coldfront.core.signals import job_start

        job_start.send(self)

    start.alters_data = True

    def terminate(self, status=JobStatusChoices.STATUS_COMPLETED, error=None):
        """Mark the job as completed with a terminal status."""
        if status not in JobStatusChoices.TERMINAL_STATE_CHOICES:
            raise ValueError(
                _("Invalid status for job termination. Choices are: {choices}").format(
                    choices=", ".join(JobStatusChoices.TERMINAL_STATE_CHOICES),
                )
            )
        self.status = status
        if error:
            self.error = error
        self.completed = timezone.now()
        self.save()

        # Notify the user (if any) of completion
        if self.user and self.notifications != JobNotificationChoices.NOTIFICATION_NEVER:
            if (
                self.notifications == JobNotificationChoices.NOTIFICATION_ALWAYS
                or status != JobStatusChoices.STATUS_COMPLETED
            ):
                from coldfront.core.notifications import Notification

                Notification(
                    user=self.user,
                    object=self,
                    event_type=self.get_event_type(),
                ).save()

        # Lazy import to avoid circular dependency: signals.py imports core.models
        from coldfront.core.signals import job_end

        job_end.send(self)

    terminate.alters_data = True

    def log(self, record: logging.LogRecord):
        """Record a LogRecord from Python's native logging in the job's log entries."""
        entry = JobLogEntry.from_logrecord(record)
        self.log_entries.append(asdict(entry))

    @classmethod
    def enqueue(
        cls,
        func,
        instance=None,
        name="",
        user=None,
        schedule_at=None,
        interval=None,
        immediate=False,
        queue_name=None,
        notifications=None,
        **kwargs,
    ):
        """
        Create a Job instance and enqueue a job using the given callable.

        Uses ``ColdFrontBackend`` (via ``Task.enqueue()``) as the enqueue path.
        The active ``COLDFRONT_TASKS_BACKEND`` setting controls whether the job
        goes to the DB (ORM) or RQ (Redis) backend.

        Args:
            func: The callable object to be enqueued for execution.
            instance: The ColdFront object to which this job pertains (optional).
            name: Name for the job (optional).
            user: The user responsible for running the job.
            schedule_at: Schedule the job to be executed at the passed date and time.
            interval: Recurrence interval (in minutes).
            immediate: Run the job immediately without scheduling it in the background.
            queue_name: Name of the queue to use. Defaults to the queue for the object type.
            notifications: Notification behavior on job completion.
        """
        if schedule_at and immediate:
            raise ValueError(_("enqueue() cannot be called with values for both schedule_at and immediate."))

        if instance:
            object_type = ContentType.objects.get_for_model(instance, for_concrete_model=False)
            object_id = instance.pk
        else:
            object_type = object_id = None

        status = JobStatusChoices.STATUS_SCHEDULED if schedule_at else JobStatusChoices.STATUS_PENDING

        job = cls(
            object_type=object_type,
            object_id=object_id,
            name=name,
            status=status,
            scheduled=schedule_at,
            interval=interval,
            user=user,
            job_id=uuid.uuid4(),
            queue_name=queue_name or "default",
            notifications=notifications if notifications is not None else JobNotificationChoices.NOTIFICATION_ALWAYS,
        )
        job.full_clean()
        job.save()

        if immediate:
            func(job_id=str(job.job_id), job=job, **kwargs)
        else:
            # Enqueue via Django Tasks (``Task.enqueue()``). The ``ColdFrontBackend``
            # handles the actual queueing and updates ``job.job_id`` to match the
            # inner backend's task ID.
            #
            # Django Tasks requires ``func`` to be a module-level function.
            # ``JobRunner.handle`` is a classmethod (bound method). Unwrap it:
            # use ``func.__func__`` (the raw function) and pass the class via
            # ``_runner_cls`` kwarg so the worker can reconstruct the call.
            if inspect.isfunction(func):
                task_func = func
            elif hasattr(func, "__func__") and hasattr(func, "__self__"):
                # Bound method (e.g., ``cls.handle`` from ``JobRunner``).
                # Use ``cls.handle.__func__`` (a real function) as the Task
                # func so ``validate_task`` passes.  Store ``_runner_cls_path``
                # as a string so the worker can reconstruct ``cls.handle()``.
                cls = func.__self__
                task_func = func.__func__
                kwargs.setdefault("_runner_cls", cls)
                kwargs.setdefault(
                    "_runner_cls_path",
                    cls.__module__ + "." + cls.__qualname__,
                )

            t = Task(
                func=task_func,
                priority=0,
                backend="default",
                queue_name=queue_name or "default",
                run_after=schedule_at,
            )
            # Pass the pre-created Job as ``_coldfront_job`` so the
            # ColdFrontBackend can update its job_id rather than creating a
            # duplicate Job record.
            t.enqueue(_coldfront_job=job, **kwargs)
            # The ColdFrontBackend already updated job.job_id; refresh the
            # instance from the DB to ensure we have the current value.
            job.refresh_from_db()

        return job
