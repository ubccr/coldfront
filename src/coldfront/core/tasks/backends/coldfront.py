# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import uuid

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.utils.module_loading import import_string
from django_tasks.backends.base import BaseTaskBackend
from django_tasks.base import TaskResult as TaskResultBase
from django_tasks.base import TaskResultStatus
from django_tasks.signals import task_enqueued
from django_tasks.utils import normalize_json

from coldfront.core.choices import JobNotificationChoices, JobStatusChoices
from coldfront.core.models import Job

__all__ = ("ColdFrontBackend",)


def _is_rq_backend():
    """Return True if COLDFRONT_TASKS_BACKEND points to the RQ backend."""
    backend_path = getattr(
        settings,
        "COLDFRONT_TASKS_BACKEND",
        "django_tasks_db.backend.DatabaseBackend",
    )
    return "django_tasks_rq" in backend_path


def _get_rq_backend():
    """Return a django-tasks-rq RQBackend instance."""
    backend_cls = import_string("django_tasks_rq.backend.RQBackend")
    inner_params = {"QUEUE": []}
    return backend_cls(alias="default", params=inner_params)


class ColdFrontBackend(BaseTaskBackend):
    """
    ColdFront task backend.

    This backend wraps an inner backend (``django-tasks-rq``) when
    ``COLDFRONT_TASKS_BACKEND`` points to the RQ backend, and handles
    queueing directly via the ``Job`` model (ORM) when using the DB backend.

    In both cases, a persistent ``Job`` record is created for every enqueued
    task, giving full UI visibility (status, logs, duration) without any
    additional work.

    Plugin authors and ColdFront apps use the native ``@task`` decorator /
    ``Task.enqueue()`` API.

    For periodic / system jobs, ``JobRunner`` remains the higher-level
    abstraction that adds interval rescheduling.
    """

    supports_defer = True
    supports_async_task = True
    supports_get_result = True
    supports_priority = True

    def __init__(self, alias, params):
        super().__init__(alias, params)
        self._use_rq = _is_rq_backend()
        if self._use_rq:
            self.inner_backend = _get_rq_backend()
            self.supports_defer = self.inner_backend.supports_defer
            self.supports_async_task = self.inner_backend.supports_async_task
            self.supports_get_result = self.inner_backend.supports_get_result
            self.supports_priority = self.inner_backend.supports_priority

    def enqueue(self, task, args, kwargs):
        self.validate_task(task)

        if self._use_rq:
            return self._enqueue_rq(task, args, kwargs)
        else:
            return self._enqueue_db(task, args, kwargs)

    async def aenqueue(self, task, args, kwargs):
        self.validate_task(task)

        if self._use_rq:
            return await self.inner_backend.aenqueue(task, args, kwargs)
        else:
            return await self._aenqueue_db(task, args, kwargs)

    def get_result(self, result_id):
        if self._use_rq:
            return self.inner_backend.get_result(result_id)
        return self._get_result_db(result_id)

    async def aget_result(self, result_id):
        if self._use_rq:
            return await self.inner_backend.aget_result(result_id)
        return await self._aget_result_db(result_id)

    # ------------------------------------------------------------------
    # RQ path — delegate to django-tasks-rq
    # ------------------------------------------------------------------

    def _enqueue_rq(self, task, args, kwargs):
        inner_result = self.inner_backend.enqueue(task, args, kwargs)

        existing_job = kwargs.get("_coldfront_job")
        if existing_job is not None:
            existing_job.job_id = uuid.UUID(inner_result.id)
            existing_job.save(update_fields=["job_id"])
            return inner_result

        meta = kwargs.get("_coldfront_job_meta") or {}
        instance = meta.get("instance")
        if instance:
            object_type = ContentType.objects.get_for_model(instance, for_concrete_model=False)
            object_id = instance.pk
        else:
            object_type = None
            object_id = None

        job = Job(
            object_type=object_type,
            object_id=object_id,
            name=meta.get("name", task.name),
            status=(JobStatusChoices.STATUS_SCHEDULED if task.run_after else JobStatusChoices.STATUS_PENDING),
            scheduled=task.run_after,
            interval=meta.get("interval"),
            user=meta.get("user"),
            job_id=uuid.UUID(inner_result.id),
            queue_name=task.queue_name or "default",
            notifications=(
                meta.get("notifications")
                if meta.get("notifications") is not None
                else JobNotificationChoices.NOTIFICATION_ALWAYS
            ),
        )
        job.full_clean()
        job.save()

        return inner_result

    # ------------------------------------------------------------------
    # DB path — direct ORM queueing via Job model
    # ------------------------------------------------------------------

    def _enqueue_db(self, task, args, kwargs):
        existing_job = kwargs.get("_coldfront_job")
        meta = kwargs.get("_coldfront_job_meta") or {}

        # Strip internal metadata from kwargs before storing args_kwargs
        # so the worker doesn't receive ColdFront-internal parameters.
        # ``_runner_cls`` (the class object) is stripped; ``_runner_cls_path``
        # (a JSON-safe string) is kept so the worker can reconstruct calls.
        clean_kwargs = {
            k: v for k, v in kwargs.items() if k not in ("_coldfront_job", "_coldfront_job_meta", "_runner_cls")
        }

        # For bound methods, ``task.module_path`` returns the function's
        # qualname (e.g. ``JobRunner.handle``) which ``import_string`` cannot
        # resolve.  Use ``_runner_cls_path`` (the class path) instead.
        runner_cls_path = kwargs.get("_runner_cls_path")
        if runner_cls_path:
            task_path = runner_cls_path
        else:
            task_path = task.module_path

        if existing_job is not None:
            # Pre-created Job from JobRunner — update it with queue fields
            existing_job.task_path = task_path
            existing_job.args_kwargs = normalize_json({"args": args, "kwargs": clean_kwargs})
            existing_job.priority = task.priority
            existing_job.save(update_fields=["task_path", "args_kwargs", "priority"])
            job_id = existing_job.job_id
        else:
            # New Job for a bare @task — create with all fields
            instance = meta.get("instance")
            if instance:
                object_type = ContentType.objects.get_for_model(instance, for_concrete_model=False)
                object_id = instance.pk
            else:
                object_type = None
                object_id = None

            job_id = uuid.uuid4()
            job = Job(
                object_type=object_type,
                object_id=object_id,
                name=meta.get("name", task.name),
                status=(JobStatusChoices.STATUS_SCHEDULED if task.run_after else JobStatusChoices.STATUS_PENDING),
                scheduled=task.run_after,
                interval=meta.get("interval"),
                user=meta.get("user"),
                job_id=job_id,
                queue_name=task.queue_name or "default",
                notifications=(
                    meta.get("notifications")
                    if meta.get("notifications") is not None
                    else JobNotificationChoices.NOTIFICATION_ALWAYS
                ),
                task_path=task_path,
                args_kwargs=normalize_json({"args": args, "kwargs": clean_kwargs}),
                priority=task.priority,
                worker_ids=[],
            )
            job.full_clean()
            job.save()

        # Build and return a TaskResult matching the Job's state.
        # Use clean_kwargs (without internal metadata) so the
        # TaskResult can serialize kwargs to JSON.
        result = TaskResultBase(
            task=task,
            id=str(job_id),
            status=TaskResultStatus.READY,
            enqueued_at=timezone.now(),
            started_at=None,
            last_attempted_at=None,
            finished_at=None,
            args=args,
            kwargs=clean_kwargs,
            backend=self.alias,
            errors=[],
            worker_ids=[],
        )
        task_enqueued.send(type(self), task_result=result)
        return result

    async def _aenqueue_db(self, task, args, kwargs):
        # Async variant — uses the same logic as _enqueue_db but saves via
        # the async Job creation path. For simplicity, falls back to sync
        # since Django's ORM async support is partial.
        return self._enqueue_db(task, args, kwargs)

    def _get_result_db(self, result_id):
        from django_tasks.exceptions import TaskResultDoesNotExist

        try:
            job = Job.objects.get(job_id=uuid.UUID(result_id))
            return job.task_result
        except (Job.DoesNotExist, ValueError, TypeError) as e:
            raise TaskResultDoesNotExist(result_id) from e

    async def _aget_result_db(self, result_id):
        from django_tasks.exceptions import TaskResultDoesNotExist

        try:
            job = await Job.objects.aget(job_id=uuid.UUID(result_id))
            return job.task_result
        except (Job.DoesNotExist, ValueError, TypeError) as e:
            raise TaskResultDoesNotExist(result_id) from e
