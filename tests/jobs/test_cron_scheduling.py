# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import uuid
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.test import TestCase
from django.utils import timezone

from coldfront.core.choices import JobStatusChoices
from coldfront.core.jobs import system_job, system_jobs
from coldfront.core.jobs.runner import JobRunner, get_next_scheduled_time, next_cron_occurrence
from coldfront.core.models import Job

#: Annual cron schedule (00:00 on January 1) — deterministic regardless of
#: the default timezone and current time of day.
YEARLY_CRON = "0 0 1 1 *"


class SimpleRunner(JobRunner):
    """A minimal JobRunner for testing."""

    def run(self):
        self.logger.info("Running simple job")


class CronDecoratorTestCase(TestCase):
    def test_decorator_registers_cron_schedule(self):
        @system_job(cron_schedule="0 9 * * *")
        class CronSyncJob(JobRunner):
            def run(self):
                pass

        self.assertIn(CronSyncJob, system_jobs)
        self.assertEqual(system_jobs[CronSyncJob]["cron_schedule"], "0 9 * * *")

    def test_decorator_rejects_invalid_cron(self):
        with self.assertRaises(ImproperlyConfigured):

            @system_job(cron_schedule="not a cron")
            class BadCronJob(JobRunner):
                def run(self):
                    pass

    def test_decorator_rejects_interval_and_cron(self):
        with self.assertRaises(ImproperlyConfigured):

            @system_job(interval=15, cron_schedule="0 9 * * *")
            class BothSchedulesJob(JobRunner):
                def run(self):
                    pass

    def test_decorator_requires_a_schedule(self):
        with self.assertRaises(ImproperlyConfigured):

            @system_job()
            class NoScheduleJob(JobRunner):
                def run(self):
                    pass


class CronJobModelValidationTestCase(TestCase):
    def _build_job(self, **kwargs):
        return Job(name="CronJob", job_id=uuid.uuid4(), **kwargs)

    def test_cron_and_interval_are_mutually_exclusive(self):
        job = self._build_job(cron_schedule="0 9 * * *", interval=60)
        with self.assertRaises(ValidationError):
            job.full_clean()

    def test_invalid_cron_rejected(self):
        job = self._build_job(cron_schedule="0 99 * * *")
        with self.assertRaises(ValidationError):
            job.full_clean()

    def test_valid_cron_accepted(self):
        job = self._build_job(cron_schedule="0 9 * * *")
        job.full_clean()  # No exception


class CronSchedulingMathTestCase(TestCase):
    def test_next_occurrence_after_base(self):
        now = timezone.now()
        next_time = next_cron_occurrence(YEARLY_CRON, now)
        self.assertGreater(next_time, now)
        self.assertEqual(timezone.localtime(next_time).strftime("%m-%d %H:%M"), "01-01 00:00")

    def test_missed_run_is_skipped(self):
        """A missed occurrence is not replayed; the next run is the first
        occurrence after the current time."""
        now = timezone.now()
        missed_base = now - timedelta(days=365 * 2)

        next_after_now = next_cron_occurrence(YEARLY_CRON, now)
        next_time = get_next_scheduled_time(Job(name="CronJob", cron_schedule=YEARLY_CRON, scheduled=missed_base))
        self.assertEqual(next_time, next_after_now)
        self.assertGreater(next_time, now)

    def test_non_periodic_job_has_no_next_time(self):
        self.assertIsNone(get_next_scheduled_time(Job(name="CronJob")))


class CronScheduleChainTestCase(TestCase):
    def test_handle_reschedules_with_cron(self):
        # Use the yearly cron: its next occurrence is months away, so the
        # assertions cannot straddle an occurrence boundary mid-test.
        cron_schedule = YEARLY_CRON

        with patch("coldfront.core.models.jobs.Task.enqueue") as mock_task_enqueue:
            mock_task_enqueue.return_value = MagicMock(id="99999999-9999-9999-9999-999999999999")

            job = SimpleRunner.enqueue_once(
                schedule_at=timezone.now(),
                cron_schedule=cron_schedule,
            )

            self.assertEqual(job.status, JobStatusChoices.STATUS_SCHEDULED)
            self.assertEqual(job.cron_schedule, cron_schedule)
            self.assertIsNone(job.interval)

            # Run the job; the finally block schedules the next occurrence.
            SimpleRunner.handle(job)
            job.refresh_from_db()
            self.assertEqual(job.status, JobStatusChoices.STATUS_COMPLETED)

        successors = Job.objects.filter(
            name=SimpleRunner.name,
            cron_schedule=cron_schedule,
            status__in=JobStatusChoices.ENQUEUED_STATE_CHOICES,
        )
        self.assertEqual(len(successors), 1)
        successor = successors[0]
        self.assertEqual(successor.interval, None)
        self.assertEqual(
            successor.scheduled,
            next_cron_occurrence(cron_schedule, job.scheduled),
        )
        self.assertGreater(successor.scheduled, timezone.now())

    def test_enqueue_once_dedupes_cron_schedules(self):
        cron_schedule = "0 9 * * *"
        schedule_at = timezone.now() + timedelta(hours=1)

        with patch("coldfront.core.models.jobs.Task.enqueue") as mock_task_enqueue:
            mock_task_enqueue.return_value = MagicMock(id="10101010-1010-1010-1010-101010101010")

            first = SimpleRunner.enqueue_once(schedule_at=schedule_at, cron_schedule=cron_schedule)
            second = SimpleRunner.enqueue_once(schedule_at=schedule_at, cron_schedule=cron_schedule)

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(len(Job.objects.filter(name=SimpleRunner.name)), 1)
