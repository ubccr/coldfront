# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from unittest.mock import MagicMock, patch

from django.test import TestCase

from coldfront.core.choices import JobStatusChoices
from coldfront.core.exceptions import JobFailed
from coldfront.core.jobs.runner import JobRunner
from coldfront.core.models import Job


class SimpleRunner(JobRunner):
    """A minimal JobRunner for testing."""

    def run(self):
        self.logger.info("Running simple job")


class FailingRunner(JobRunner):
    """A JobRunner that raises JobFailed."""

    def run(self):
        raise JobFailed("Controlled failure")


class ErroringRunner(JobRunner):
    """A JobRunner that raises an unexpected exception."""

    def run(self):
        raise ValueError("Unexpected error")


class JobRunnerTestCase(TestCase):
    def test_runner_executes_successfully(self):
        job = Job.objects.create(
            name="SimpleRunner",
            job_id="11111111-1111-1111-1111-111111111111",
        )
        SimpleRunner.handle(job)
        job.refresh_from_db()
        self.assertEqual(job.status, JobStatusChoices.STATUS_COMPLETED)
        self.assertIsNotNone(job.completed)

    def test_runner_calls_start_and_terminate(self):
        job = Job.objects.create(
            name="SimpleRunner",
            job_id="22222222-2222-2222-2222-222222222222",
        )
        with patch.object(job, "start") as mock_start, patch.object(job, "terminate") as mock_terminate:
            SimpleRunner.handle(job)
            mock_start.assert_called_once()
            mock_terminate.assert_called_once()

    def test_runner_handles_job_failed(self):
        job = Job.objects.create(
            name="FailingRunner",
            job_id="33333333-3333-3333-3333-333333333333",
        )
        FailingRunner.handle(job)
        job.refresh_from_db()
        self.assertEqual(job.status, JobStatusChoices.STATUS_FAILED)

    def test_runner_handles_unexpected_error(self):
        job = Job.objects.create(
            name="ErroringRunner",
            job_id="44444444-4444-4444-4444-444444444444",
        )
        ErroringRunner.handle(job)
        job.refresh_from_db()
        self.assertEqual(job.status, JobStatusChoices.STATUS_ERRORED)
        self.assertIn("ValueError", job.error)

    def test_runner_name_from_class(self):
        self.assertEqual(SimpleRunner.name, "SimpleRunner")

    def test_runner_name_from_meta(self):
        class NamedRunner(JobRunner):
            class Meta:
                name = "Custom Name"

            def run(self):
                pass

        self.assertEqual(NamedRunner.name, "Custom Name")

    def test_runner_enqueue_creates_job(self):
        with patch("coldfront.core.models.jobs.Task.enqueue") as mock_task_enqueue:
            mock_task_enqueue.return_value = MagicMock(id="11111111-1111-1111-1111-111111111111")

            job = SimpleRunner.enqueue(name="Test Enqueue", user=None)

            self.assertEqual(job.name, "Test Enqueue")
            self.assertEqual(job.status, JobStatusChoices.STATUS_PENDING)
            mock_task_enqueue.assert_called_once()

    def test_runner_get_jobs_filters_by_name(self):
        Job.objects.create(
            name="SimpleRunner",
            job_id="55555555-5555-5555-5555-555555555555",
        )
        Job.objects.create(
            name="OtherRunner",
            job_id="66666666-6666-6666-6666-666666666666",
        )
        jobs = SimpleRunner.get_jobs()
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].name, "SimpleRunner")

    def test_runner_logs_during_run(self):
        job = Job.objects.create(
            name="SimpleRunner",
            job_id="77777777-7777-7777-7777-777777777777",
        )
        SimpleRunner.handle(job)
        job.refresh_from_db()
        self.assertGreater(len(job.log_entries), 0)
        self.assertEqual(job.log_entries[0]["level"], "INFO")

    def test_runner_enqueue_once_skips_duplicate(self):
        Job.objects.create(
            name="SimpleRunner",
            job_id="88888888-8888-8888-8888-888888888888",
            status=JobStatusChoices.STATUS_PENDING,
        )
        with patch("coldfront.core.models.jobs.Task.enqueue") as mock_task_enqueue:
            mock_task_enqueue.return_value = MagicMock(id="88888888-8888-8888-8888-888888888888")

            result = SimpleRunner.enqueue_once(interval=15)
            self.assertIsNotNone(result)

    def test_runner_get_jobs_with_instance(self):
        from django.contrib.contenttypes.models import ContentType

        from coldfront.users.models import User

        user = User.objects.create(username="testuser")
        ct = ContentType.objects.get_for_model(User)
        job = Job.objects.create(
            name="SimpleRunner",
            job_id="99999999-9999-9999-9999-999999999999",
            object_type=ct,
            object_id=user.pk,
        )
        jobs = SimpleRunner.get_jobs(instance=user)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].pk, job.pk)
