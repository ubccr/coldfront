# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import logging
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from coldfront.core.choices import JobNotificationChoices, JobStatusChoices
from coldfront.core.models import Job, JobLogEntry


class JobModelTestCase(TestCase):
    def test_job_creation(self):
        job = Job.objects.create(
            name="Test Job",
            job_id="11111111-1111-1111-1111-111111111111",
        )
        self.assertEqual(job.name, "Test Job")
        self.assertEqual(job.status, JobStatusChoices.STATUS_PENDING)
        self.assertIsNotNone(job.created)
        self.assertIsNone(job.started)
        self.assertIsNone(job.completed)

    def test_job_status_choices(self):
        job = Job.objects.create(
            name="Test Job",
            status=JobStatusChoices.STATUS_RUNNING,
            job_id="22222222-2222-2222-2222-222222222222",
        )
        self.assertEqual(job.status, "running")

    def test_job_start(self):
        job = Job.objects.create(
            name="Test Job",
            job_id="33333333-3333-3333-3333-333333333333",
        )
        job.start()
        self.assertEqual(job.status, JobStatusChoices.STATUS_RUNNING)
        self.assertIsNotNone(job.started)

    def test_job_start_idempotent(self):
        job = Job.objects.create(
            name="Test Job",
            job_id="44444444-4444-4444-4444-444444444444",
        )
        job.start()
        started = job.started
        job.start()  # second call should not change started
        self.assertEqual(job.started, started)

    def test_job_terminate_completed(self):
        job = Job.objects.create(
            name="Test Job",
            job_id="55555555-5555-5555-5555-555555555555",
        )
        job.start()
        job.terminate(status=JobStatusChoices.STATUS_COMPLETED)
        self.assertEqual(job.status, JobStatusChoices.STATUS_COMPLETED)
        self.assertIsNotNone(job.completed)

    def test_job_terminate_failed(self):
        job = Job.objects.create(
            name="Test Job",
            job_id="66666666-6666-6666-6666-666666666666",
        )
        job.start()
        job.terminate(status=JobStatusChoices.STATUS_FAILED, error="Something went wrong")
        self.assertEqual(job.status, JobStatusChoices.STATUS_FAILED)
        self.assertEqual(job.error, "Something went wrong")

    def test_job_terminate_invalid_status(self):
        job = Job.objects.create(
            name="Test Job",
            job_id="77777777-7777-7777-7777-777777777777",
        )
        with self.assertRaises(ValueError):
            job.terminate(status="invalid_status")

    def test_job_log_entry(self):
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        entry = JobLogEntry.from_logrecord(record)
        self.assertEqual(entry.level, "INFO")
        self.assertEqual(entry.message, "Test message")

    def test_job_log(self):
        job = Job.objects.create(
            name="Test Job",
            job_id="88888888-8888-8888-8888-888888888888",
        )
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test log entry",
            args=(),
            exc_info=None,
        )
        job.log(record)
        self.assertEqual(len(job.log_entries), 1)
        self.assertEqual(job.log_entries[0]["level"], "INFO")
        self.assertEqual(job.log_entries[0]["message"], "Test log entry")

    def test_duration_property(self):
        now = timezone.now()
        job = Job.objects.create(
            name="Test Job",
            job_id="99999999-9999-9999-9999-999999999999",
            started=now,
            completed=now + timezone.timedelta(minutes=5, seconds=30),
        )
        self.assertEqual(job.duration, "5 minutes, 30.00 seconds")

    def test_duration_none_when_not_completed(self):
        job = Job.objects.create(
            name="Test Job",
            job_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            started=timezone.now(),
        )
        self.assertIsNone(job.duration)

    def test_str(self):
        job = Job.objects.create(
            name="Test Job",
            job_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        )
        self.assertEqual(str(job), "Test Job")

    def test_notification_choices(self):
        job = Job.objects.create(
            name="Test Job",
            job_id="cccccccc-cccc-cccc-cccc-cccccccccccc",
            notifications=JobNotificationChoices.NOTIFICATION_NEVER,
        )
        self.assertEqual(job.notifications, "never")

    def test_get_status_color(self):
        job = Job.objects.create(
            name="Test Job",
            status=JobStatusChoices.STATUS_COMPLETED,
            job_id="dddddddd-dddd-dddd-dddd-dddddddddddd",
        )
        self.assertEqual(job.get_status_color(), "success")

    def test_get_event_type_completed(self):
        job = Job.objects.create(
            name="Test Job",
            status=JobStatusChoices.STATUS_COMPLETED,
            job_id="eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
        )
        from coldfront.core.events import JOB_COMPLETED

        self.assertEqual(job.get_event_type(), JOB_COMPLETED)

    def test_get_event_type_failed(self):
        job = Job.objects.create(
            name="Test Job",
            status=JobStatusChoices.STATUS_FAILED,
            job_id="ffffffff-ffff-ffff-ffff-ffffffffffff",
        )
        from coldfront.core.events import JOB_FAILED

        self.assertEqual(job.get_event_type(), JOB_FAILED)

    def test_get_event_type_errored(self):
        job = Job.objects.create(
            name="Test Job",
            status=JobStatusChoices.STATUS_ERRORED,
            job_id="11111111-1111-1111-1111-111111111112",
        )
        from coldfront.core.events import JOB_ERRORED

        self.assertEqual(job.get_event_type(), JOB_ERRORED)

    def test_get_event_type_pending(self):
        job = Job.objects.create(
            name="Test Job",
            status=JobStatusChoices.STATUS_PENDING,
            job_id="22222222-2222-2222-2222-222222222221",
        )
        self.assertIsNone(job.get_event_type())

    def test_get_absolute_url(self):
        job = Job.objects.create(
            name="Test Job",
            job_id="33333333-3333-3333-3333-333333333331",
        )
        # URL pattern is not registered yet (Phase 3), so we test the
        # method returns the expected format by patching reverse.
        expected_url = "/core/jobs/1/"
        with patch("coldfront.core.models.jobs.reverse") as mock_reverse:
            mock_reverse.return_value = expected_url
            url = job.get_absolute_url()
            self.assertEqual(url, expected_url)
            mock_reverse.assert_called_once_with("core:job", args=[job.pk])

    def test_interval_validation(self):
        job = Job.objects.create(
            name="Test Job",
            job_id="44444444-4444-4444-4444-444444444441",
            interval=15,
        )
        self.assertEqual(job.interval, 15)

    def test_queue_name(self):
        job = Job.objects.create(
            name="Test Job",
            job_id="55555555-5555-5555-5555-555555555551",
            queue_name="slurm",
        )
        self.assertEqual(job.queue_name, "slurm")

    def test_data_field(self):
        job = Job.objects.create(
            name="Test Job",
            job_id="66666666-6666-6666-6666-666666666661",
            data={"key": "value"},
        )
        self.assertEqual(job.data, {"key": "value"})
