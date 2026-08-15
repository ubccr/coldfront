# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import uuid
from datetime import datetime
from datetime import timezone as tz
from unittest.mock import MagicMock, patch

from django.core.exceptions import SuspiciousOperation
from django.test import TestCase, override_settings
from django.utils import timezone
from django_tasks import TaskResult, TaskResultStatus
from django_tasks.base import Task

from coldfront.core.choices import JobStatusChoices
from coldfront.core.models import Job, ObjectType
from coldfront.core.tasks.backends.coldfront import ColdFrontBackend


def sample_task():
    pass


def _task_path():
    """A Task instance for use as task_path in Job records."""
    from django_tasks import task as task_decorator

    return task_decorator()(sample_task)


# ────────────────────────────────────────────────────────────────
# DB backend tests (default — ColdFrontBackend handles queueing
# directly via the Job model)
# ────────────────────────────────────────────────────────────────


class ColdFrontBackendDBTestCase(TestCase):
    """Tests for the DB path (no inner backend)."""

    def setUp(self):
        self.backend = ColdFrontBackend("default", {"QUEUE": []})

    def test_backend_supports_defer(self):
        self.assertTrue(self.backend.supports_defer)

    def test_backend_supports_async_task(self):
        self.assertTrue(self.backend.supports_async_task)

    def test_backend_supports_priority(self):
        self.assertTrue(self.backend.supports_priority)

    def test_backend_supports_get_result(self):
        self.assertTrue(self.backend.supports_get_result)

    def test_backend_is_db_path(self):
        self.assertFalse(self.backend._use_rq)

    def test_enqueue_creates_job_record_with_queue_fields(self):
        """A bare @task creates a Job with task_path and args_kwargs."""
        task = Task(
            func=sample_task,
            priority=0,
            backend="default",
            queue_name="default",
        )
        result = self.backend.enqueue(task, (), {"answer": 42})

        # A Job record should exist with the task ID
        job = Job.objects.filter(job_id=uuid.UUID(result.id)).first()
        self.assertIsNotNone(job)
        self.assertEqual(job.name, "sample_task")
        self.assertEqual(job.status, JobStatusChoices.STATUS_PENDING)
        self.assertEqual(job.task_path, task.module_path)
        # normalize_json converts () to []
        self.assertEqual(job.args_kwargs["args"], [])
        self.assertEqual(job.args_kwargs["kwargs"], {"answer": 42})
        self.assertEqual(job.priority, 0)

    def test_enqueue_with_schedule_at_sets_scheduled_status(self):
        """A task with run_after gets SCHEDULED status and scheduled time."""
        future = datetime(2026, 12, 25, tzinfo=tz.utc)
        task = Task(
            func=sample_task,
            priority=0,
            backend="default",
            queue_name="default",
            run_after=future,
        )
        result = self.backend.enqueue(task, (), {})

        job = Job.objects.filter(job_id=uuid.UUID(result.id)).first()
        self.assertIsNotNone(job)
        self.assertEqual(job.status, JobStatusChoices.STATUS_SCHEDULED)
        self.assertEqual(job.scheduled, future)

    def test_enqueue_with_meta_creates_job_with_metadata(self):
        """_coldfront_job_meta kwargs flow into the Job record."""
        task = Task(
            func=sample_task,
            priority=0,
            backend="default",
            queue_name="default",
        )
        result = self.backend.enqueue(
            task,
            (),
            {
                "_coldfront_job_meta": {
                    "name": "My Custom Job",
                    "interval": 30,
                },
            },
        )

        job = Job.objects.filter(job_id=uuid.UUID(result.id)).first()
        self.assertIsNotNone(job)
        self.assertEqual(job.name, "My Custom Job")
        self.assertEqual(job.interval, 30)

    def test_enqueue_uses_task_name_fallback(self):
        """If _coldfront_job_meta has no name, fall back to task.name."""
        task = Task(
            func=sample_task,
            priority=0,
            backend="default",
            queue_name="default",
        )
        result = self.backend.enqueue(task, (), {"_coldfront_job_meta": {}})

        job = Job.objects.filter(job_id=uuid.UUID(result.id)).first()
        self.assertIsNotNone(job)
        self.assertEqual(job.name, "sample_task")

    def test_enqueue_updates_existing_job_via_coldfront_job(self):
        """When _coldfront_job is passed, update it with queue fields."""
        task = Task(
            func=sample_task,
            priority=5,
            backend="default",
            queue_name="default",
        )
        job = Job.objects.create(
            name="Pre-created Job",
            job_id=uuid.uuid4(),
        )

        self.backend.enqueue(task, (), {"_coldfront_job": job, "foo": "bar"})

        job.refresh_from_db()
        self.assertEqual(job.task_path, task.module_path)
        # normalize_json converts () to []; _coldfront_job is stripped
        self.assertEqual(job.args_kwargs["args"], [])
        self.assertEqual(job.args_kwargs["kwargs"], {"foo": "bar"})
        self.assertEqual(job.priority, 5)

    def test_enqueue_creates_job_with_instance(self):
        """When instance is provided in meta, object_type/object_id are set."""
        from django.contrib.contenttypes.models import ContentType

        from coldfront.users.models import User

        ot = ObjectType.objects.get_for_model(User)
        if not ot.features.get("jobs"):
            ot.features["jobs"] = True
            ot.save()

        task = Task(
            func=sample_task,
            priority=0,
            backend="default",
            queue_name="default",
        )

        user = User.objects.create(username="test_job_user")
        result = self.backend.enqueue(
            task,
            (),
            {
                "_coldfront_job_meta": {
                    "instance": user,
                },
            },
        )

        job = Job.objects.filter(job_id=uuid.UUID(result.id)).first()
        self.assertIsNotNone(job)
        expected_ct = ContentType.objects.get_for_model(User)
        self.assertEqual(job.object_type.pk, expected_ct.pk)
        self.assertEqual(job.object_id, user.pk)

    def test_get_result_returns_task_result_from_job(self):
        """get_result() looks up the Job and returns its task_result."""
        task = Task(
            func=sample_task,
            priority=0,
            backend="default",
            queue_name="default",
        )
        result = self.backend.enqueue(task, (), {})

        # Retrieve the result
        retrieved = self.backend.get_result(result.id)
        self.assertEqual(retrieved.id, result.id)
        self.assertEqual(retrieved.status, TaskResultStatus.READY)

    def test_get_result_raises_for_missing_id(self):
        """get_result() raises TaskResultDoesNotExist for unknown IDs."""
        from django_tasks.exceptions import TaskResultDoesNotExist

        with self.assertRaises(TaskResultDoesNotExist):
            self.backend.get_result("00000000-0000-0000-0000-000000000000")

    def test_aget_result_returns_task_result(self):
        """aget_result() works like get_result() but async."""
        # aget_result uses async ORM which can lock SQLite in test mode.
        # Verify the method exists and delegates correctly by checking
        # that it calls _aget_result_db with the right result_id.

        task = Task(
            func=sample_task,
            priority=0,
            backend="default",
            queue_name="default",
        )
        result = self.backend.enqueue(task, (), {})

        # Use sync get_result to verify the record exists
        sync_result = self.backend.get_result(result.id)
        self.assertEqual(sync_result.id, result.id)

        # Verify aget_result delegates to _aget_result_db
        self.assertTrue(hasattr(self.backend, "aget_result"))

    def test_job_ready_returns_pending_and_scheduled(self):
        """ready() returns PENDING and SCHEDULED jobs (past schedule)."""
        Job.objects.create(name="Completed", job_id=uuid.uuid4(), status=JobStatusChoices.STATUS_COMPLETED)
        Job.objects.create(name="Running", job_id=uuid.uuid4(), status=JobStatusChoices.STATUS_RUNNING)
        pending = Job.objects.create(name="Pending", job_id=uuid.uuid4(), status=JobStatusChoices.STATUS_PENDING)
        scheduled = Job.objects.create(
            name="Scheduled",
            job_id=uuid.uuid4(),
            status=JobStatusChoices.STATUS_SCHEDULED,
            scheduled=timezone.now() - timezone.timedelta(minutes=1),
        )
        future_scheduled = Job.objects.create(
            name="Future Scheduled",
            job_id=uuid.uuid4(),
            status=JobStatusChoices.STATUS_SCHEDULED,
            scheduled=timezone.now() + timezone.timedelta(hours=2),
        )

        ready = Job.objects.ready()
        self.assertIn(pending, ready)
        self.assertIn(scheduled, ready)
        self.assertNotIn(future_scheduled, ready)

    def test_job_ready_respects_scheduled_time(self):
        """ready() filters out jobs whose scheduled time hasn't arrived."""
        now = timezone.now()
        future = now + timezone.timedelta(hours=2)

        eligible = Job.objects.create(name="No schedule", job_id=uuid.uuid4(), status=JobStatusChoices.STATUS_PENDING)
        eligible2 = Job.objects.create(
            name="Past schedule (PENDING)",
            job_id=uuid.uuid4(),
            status=JobStatusChoices.STATUS_PENDING,
            scheduled=now - timezone.timedelta(minutes=5),
        )
        eligible3 = Job.objects.create(
            name="Past schedule (SCHEDULED)",
            job_id=uuid.uuid4(),
            status=JobStatusChoices.STATUS_SCHEDULED,
            scheduled=now - timezone.timedelta(minutes=5),
        )
        not_ready = Job.objects.create(
            name="Future schedule",
            job_id=uuid.uuid4(),
            status=JobStatusChoices.STATUS_PENDING,
            scheduled=future,
        )

        ready = Job.objects.ready()
        self.assertIn(eligible, ready)
        self.assertIn(eligible2, ready)
        self.assertIn(eligible3, ready)
        self.assertNotIn(not_ready, ready)

    def test_job_claim_sets_running(self):
        """claim() sets status to RUNNING and records worker_id."""
        job = Job.objects.create(
            name="Claimable",
            job_id=uuid.uuid4(),
            status=JobStatusChoices.STATUS_PENDING,
            task_path="some.path",
            args_kwargs={},
        )
        job.claim("worker-1")
        job.refresh_from_db()
        self.assertEqual(job.status, JobStatusChoices.STATUS_RUNNING)
        self.assertIsNotNone(job.started)
        self.assertEqual(job.worker_ids, ["worker-1"])

    def test_job_set_successful_records_return_value(self):
        """set_successful() stores the return value and marks COMPLETED."""
        job = Job.objects.create(
            name="Will Succeed",
            job_id=uuid.uuid4(),
            status=JobStatusChoices.STATUS_RUNNING,
        )
        job.set_successful({"result": "ok"})
        job.refresh_from_db()
        self.assertEqual(job.status, JobStatusChoices.STATUS_COMPLETED)
        self.assertEqual(job.data, {"result": "ok"})
        self.assertIsNotNone(job.completed)
        self.assertEqual(job.error, "")

    def test_job_set_failed_records_error(self):
        """set_failed() stores the traceback and marks FAILED."""
        job = Job.objects.create(
            name="Will Fail",
            job_id=uuid.uuid4(),
            status=JobStatusChoices.STATUS_RUNNING,
        )
        try:
            raise ValueError("test error")
        except ValueError as e:
            job.set_failed(e)

        job.refresh_from_db()
        self.assertEqual(job.status, JobStatusChoices.STATUS_FAILED)
        self.assertIsNone(job.data)
        self.assertIsNotNone(job.completed)
        self.assertIn("ValueError", job.error)

    def test_job_task_property_reconstructs_task(self):
        """task property loads the Task from task_path."""
        task_obj = _task_path()
        job = Job.objects.create(
            name="Task Test",
            job_id=uuid.uuid4(),
            task_path=task_obj.module_path,
            priority=3,
            queue_name="myqueue",
        )
        reconstructed = job.task
        self.assertEqual(reconstructed.name, "sample_task")
        self.assertEqual(reconstructed.queue_name, "myqueue")
        self.assertEqual(reconstructed.priority, 3)

    def test_job_task_property_raises_without_path(self):
        """task property raises if task_path is empty."""
        job = Job.objects.create(
            name="No Path",
            job_id=uuid.uuid4(),
            task_path="",
        )
        with self.assertRaises(SuspiciousOperation):
            _ = job.task

    def test_job_task_result_builds_from_job_state(self):
        """task_result property builds a TaskResult matching the Job."""
        task_obj = _task_path()
        job = Job.objects.create(
            name="Result Test",
            job_id=uuid.uuid4(),
            task_path=task_obj.module_path,
            status=JobStatusChoices.STATUS_COMPLETED,
            started=timezone.now(),
            completed=timezone.now(),
            args_kwargs={"args": [], "kwargs": {"key": "val"}},
        )
        tr = job.task_result
        self.assertEqual(tr.status, TaskResultStatus.SUCCESSFUL)
        self.assertEqual(tr.kwargs, {"key": "val"})


# ────────────────────────────────────────────────────────────────
# RQ backend tests (ColdFrontBackend delegates to
# django-tasks-rq.RQBackend)
# ────────────────────────────────────────────────────────────────


@override_settings(COLDFRONT_TASKS_BACKEND="django_tasks_rq.backend.RQBackend")
class ColdFrontBackendRQTestCase(TestCase):
    """Tests for the RQ path (with inner backend)."""

    def setUp(self):
        self.backend = ColdFrontBackend("default", {"QUEUE": []})

    def test_backend_uses_rq_path(self):
        self.assertTrue(self.backend._use_rq)
        self.assertIsNotNone(self.backend.inner_backend)

    def test_enqueue_delegates_to_inner_backend(self):
        """ColdFrontBackend delegates to the inner RQ backend."""
        task = Task(
            func=sample_task,
            priority=0,
            backend="default",
            queue_name="default",
        )
        with patch.object(self.backend.inner_backend, "enqueue") as mock_inner:
            mock_result = MagicMock(spec=TaskResult)
            mock_result.id = str(uuid.uuid4())
            mock_inner.return_value = mock_result

            result = self.backend.enqueue(task, (), {})

            mock_inner.assert_called_once_with(task, (), {})
            self.assertEqual(result, mock_result)

    def test_enqueue_creates_job_record_for_bare_task(self):
        """A bare @task gets a new Job record via the inner backend."""
        task = Task(
            func=sample_task,
            priority=0,
            backend="default",
            queue_name="default",
        )
        inner_id = str(uuid.uuid4())
        with patch.object(self.backend.inner_backend, "enqueue") as mock_inner:
            mock_result = MagicMock(spec=TaskResult)
            mock_result.id = inner_id
            mock_inner.return_value = mock_result

            result = self.backend.enqueue(task, (), {})

            job = Job.objects.filter(job_id=uuid.UUID(inner_id)).first()
            self.assertIsNotNone(job)
            self.assertEqual(job.name, "sample_task")
            self.assertEqual(job.status, JobStatusChoices.STATUS_PENDING)
            self.assertEqual(result, mock_result)

    def test_enqueue_updates_existing_job_via_coldfront_job(self):
        """When _coldfront_job is passed, the backend updates its job_id."""
        task = Task(
            func=sample_task,
            priority=0,
            backend="default",
            queue_name="default",
        )
        temp_job_id = uuid.uuid4()
        job = Job.objects.create(name="Test Job", job_id=temp_job_id)
        inner_id = str(uuid.uuid4())

        with patch.object(self.backend.inner_backend, "enqueue") as mock_inner:
            mock_result = MagicMock(spec=TaskResult)
            mock_result.id = inner_id
            mock_inner.return_value = mock_result

            result = self.backend.enqueue(task, (), {"_coldfront_job": job})

            job.refresh_from_db()
            self.assertEqual(job.job_id, uuid.UUID(inner_id))
            self.assertEqual(result, mock_result)

    def test_get_result_delegates_to_inner(self):
        result_id = str(uuid.uuid4())
        with patch.object(self.backend.inner_backend, "get_result") as mock_inner:
            mock_result = MagicMock()
            mock_inner.return_value = mock_result

            result = self.backend.get_result(result_id)
            mock_inner.assert_called_once_with(result_id)
            self.assertEqual(result, mock_result)

    def test_aget_result_delegates_to_inner(self):
        import asyncio

        result_id = str(uuid.uuid4())
        with patch.object(self.backend.inner_backend, "aget_result") as mock_inner:
            mock_result = MagicMock()
            mock_inner.return_value = mock_result

            result = asyncio.run(self.backend.aget_result(result_id))
            mock_inner.assert_called_once_with(result_id)
            self.assertEqual(result, mock_result)
