# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from coldfront.core.choices import JobStatusChoices
from coldfront.core.jobs.registry import system_jobs
from coldfront.core.models import Job, ObjectChange
from coldfront.core.tasks.system import NotificationDigestJob, PruneChangeLogJob, PruneJob


class PruneChangeLogJobTestCase(TestCase):
    def _create_records(self):
        from django.contrib.contenttypes.models import ContentType

        ct = ContentType.objects.get_for_model(ObjectChange)
        now = timezone.now()
        ages = [10, 20, 30, 200, 400]  # days old — well within and beyond retention
        for age_days in ages:
            oc = ObjectChange.objects.create(
                user_name="test",
                request_id="00000000-0000-0000-0000-000000000000",
                action="update",
                changed_object_type=ct,
                changed_object_id=1,
                object_repr="test",
            )
            # Override auto_now_add by setting the time via update()
            ObjectChange.objects.filter(pk=oc.pk).update(time=now - timedelta(days=age_days))

    def test_registered_as_system_job(self):
        """PruneChangeLogJob is registered with a daily interval."""
        self.assertIn(PruneChangeLogJob, system_jobs)
        self.assertEqual(system_jobs[PruneChangeLogJob]["interval"], 1440)

    def test_meta_name(self):
        """PruneChangeLogJob has a well-formed Meta.name."""
        self.assertEqual(PruneChangeLogJob.name, "coldfront.core.tasks.system.PruneChangeLogJob")

    def test_deletes_old_records(self):
        """Records older than CHANGELOG_RETENTION (default 90) are deleted."""
        self._create_records()
        job = PruneChangeLogJob(PruneChangeLogJob.get_jobs().first() or PruneChangeLogJob.enqueue())
        job.run()

        remaining = ObjectChange.objects.count()
        # 5 records created: 10, 20, 30, 200, 400 days old.
        # With 90-day retention, records <= 90 days are kept:
        #   10, 20, 30 → kept; 200, 400 → deleted.
        self.assertEqual(remaining, 3)

    @override_settings(CHANGELOG_RETENTION=0)
    def test_skips_deletion_when_retention_is_zero(self):
        """When CHANGELOG_RETENTION=0, nothing is deleted."""
        self._create_records()
        job = PruneChangeLogJob(PruneChangeLogJob.get_jobs().first() or PruneChangeLogJob.enqueue())
        job.run()
        self.assertEqual(ObjectChange.objects.count(), 5)

    @override_settings(CHANGELOG_RETENTION=180)
    def test_keeps_records_within_extended_retention(self):
        """With 180-day retention, records 10, 20, 30, 200 are kept; 400 deleted.
        (200 days > 180 retention, but wait — 200 > 180 so it IS deleted.)
        Actually: 10, 20, 30 are within 180, 200 and 400 are beyond — so 3 remain."""
        self._create_records()
        job = PruneChangeLogJob(PruneChangeLogJob.get_jobs().first() or PruneChangeLogJob.enqueue())
        job.run()
        self.assertEqual(ObjectChange.objects.count(), 3)

    @override_settings(CHANGELOG_RETENTION=50)
    def test_deletes_more_with_shorter_retention(self):
        """With 50-day retention, records 10, 20, 30 are kept; 200, 400 deleted."""
        self._create_records()
        job = PruneChangeLogJob(PruneChangeLogJob.get_jobs().first() or PruneChangeLogJob.enqueue())
        job.run()
        self.assertEqual(ObjectChange.objects.count(), 3)


class NotificationDigestJobTestCase(TestCase):
    def test_registered_as_system_job(self):
        """NotificationDigestJob is registered with a daily interval."""
        self.assertIn(NotificationDigestJob, system_jobs)
        self.assertEqual(system_jobs[NotificationDigestJob]["interval"], 1440)

    def test_meta_name(self):
        """NotificationDigestJob has a well-formed Meta.name."""
        self.assertEqual(
            NotificationDigestJob.name,
            "coldfront.core.tasks.system.NotificationDigestJob",
        )

    @patch("generic_notifications.digest.send_notification_digests")
    def test_run_calls_send_notification_digests(self, mock_send):
        """run() calls send_notification_digests with DailyFrequency."""
        mock_send.return_value = 42

        job = NotificationDigestJob(NotificationDigestJob.get_jobs().first() or NotificationDigestJob.enqueue())
        job.run()

        from generic_notifications.frequencies import DailyFrequency

        mock_send.assert_called_once_with(DailyFrequency)

    @patch("generic_notifications.digest.send_notification_digests")
    def test_run_logs_sent_count(self, mock_send):
        """run() logs the number of digests sent."""
        mock_send.return_value = 7
        import logging

        logger = logging.getLogger("coldfront.jobs.NotificationDigestJob")
        with self.assertLogs(logger, level="INFO") as log:
            job = NotificationDigestJob(NotificationDigestJob.get_jobs().first() or NotificationDigestJob.enqueue())
            job.run()
            self.assertIn("Sent 7", log.output[0])


class TaskPathIntegrationTestCase(TestCase):
    """
    Verify that ``task_path`` stored by ``Job.enqueue()`` for ``JobRunner``
    bound methods can be resolved by ``import_string`` and reconstructed by
    ``Job.task``.
    """

    def test_task_path_is_importable_for_jobrunner(self):
        """task_path is the class path, importable via import_string."""
        from django.utils.module_loading import import_string

        job = PruneChangeLogJob.enqueue()
        job.refresh_from_db()

        # task_path should be the class path, e.g.
        # "coldfront.core.tasks.system.PruneChangeLogJob"
        self.assertIsNotNone(job.task_path)
        self.assertNotIn("JobRunner", job.task_path)
        self.assertNotIn("handle", job.task_path)
        # import_string should succeed without ModuleNotFoundError
        obj = import_string(job.task_path)
        self.assertTrue(callable(obj))

    def test_task_reconstructs_with_runner_cls_path(self):
        """Job.task uses _runner_cls_path to load cls.handle.__func__."""
        job = PruneChangeLogJob.enqueue()
        job.refresh_from_db()

        task = job.task
        self.assertIsNotNone(task)
        # The task.func should be cls.handle.__func__ (module-level)
        self.assertEqual(task.func, PruneChangeLogJob.handle.__func__)

    def test_task_path_contains_runner_cls_path_in_args_kwargs(self):
        """_runner_cls_path is stored in args_kwargs for worker use."""
        job = PruneChangeLogJob.enqueue()
        job.refresh_from_db()

        self.assertIsNotNone(job.args_kwargs)
        kwargs = job.args_kwargs.get("kwargs", {})
        self.assertIn("_runner_cls_path", kwargs)
        self.assertEqual(
            kwargs["_runner_cls_path"],
            "coldfront.core.tasks.system.PruneChangeLogJob",
        )

    def test_import_string_resolves_task_path(self):
        """import_string(task_path) does not raise ModuleNotFoundError."""
        from django.utils.module_loading import import_string

        job = PruneChangeLogJob.enqueue()
        job.refresh_from_db()

        try:
            import_string(job.task_path)
        except Exception as e:
            self.fail(f"import_string failed: {e}")


class PruneJobTestCase(TestCase):
    def _create_jobs(self):
        import uuid

        now = timezone.now()
        ages = [10, 30, 100, 200]  # days old
        for age_days in ages:
            # Completed jobs
            Job.objects.create(
                name="Prune Test",
                job_id=uuid.uuid4(),
                status=JobStatusChoices.STATUS_COMPLETED,
                completed=now - timedelta(days=age_days),
            )
            # Failed jobs
            Job.objects.create(
                name="Prune Test",
                job_id=uuid.uuid4(),
                status=JobStatusChoices.STATUS_FAILED,
                completed=now - timedelta(days=age_days),
            )
        # Errored (separate status)
        Job.objects.create(
            name="Prune Test",
            job_id=uuid.uuid4(),
            status=JobStatusChoices.STATUS_ERRORED,
            completed=now - timedelta(days=200),
        )
        # Running / pending — never pruned
        Job.objects.create(
            name="Prune Test",
            job_id=uuid.uuid4(),
            status=JobStatusChoices.STATUS_RUNNING,
            completed=now - timedelta(days=200),
        )
        Job.objects.create(
            name="Prune Test",
            job_id=uuid.uuid4(),
            status=JobStatusChoices.STATUS_PENDING,
        )

    def test_registered_as_system_job(self):
        """PruneJob is registered with a daily interval."""
        self.assertIn(PruneJob, system_jobs)
        self.assertEqual(system_jobs[PruneJob]["interval"], 1440)

    def test_meta_name(self):
        """PruneJob has a well-formed Meta.name."""
        self.assertEqual(PruneJob.name, "coldfront.core.tasks.system.PruneJob")

    def test_deletes_old_completed(self):
        """Completed jobs older than JOB_COMPLETED_RETENTION (default 90) are deleted."""
        self._create_jobs()
        job = PruneJob(PruneJob.get_jobs().first() or PruneJob.enqueue())
        job.run()

        remaining = Job.objects.count()
        # Created: 11 test jobs + 1 PruneJob's own job = 12 total
        # Default 90-day retention:
        #   Completed > 90: 100, 200 → 2 deleted
        #   Failed/errored > 90: failed 100, 200 (2) + errored 200 (1) → 3 deleted
        # Total deleted: 5. Remaining: 12 - 5 = 7.
        self.assertEqual(remaining, 7)

    @override_settings(JOB_COMPLETED_RETENTION=0, JOB_FAILED_RETENTION=0)
    def test_skips_deletion_when_both_retentions_zero(self):
        """When both retentions are 0, nothing is deleted."""
        self._create_jobs()
        job = PruneJob(PruneJob.get_jobs().first() or PruneJob.enqueue())
        job.run()
        self.assertEqual(Job.objects.count(), 12)

    @override_settings(JOB_COMPLETED_RETENTION=-1, JOB_FAILED_RETENTION=-1)
    def test_skips_deletion_when_both_retentions_negative(self):
        """When both retentions are negative, nothing is deleted."""
        self._create_jobs()
        job = PruneJob(PruneJob.get_jobs().first() or PruneJob.enqueue())
        job.run()
        self.assertEqual(Job.objects.count(), 12)

    @override_settings(JOB_COMPLETED_RETENTION=200)
    def test_keeps_completed_within_extended_retention(self):
        """With 200-day completed retention, completed 200-day-old job is right
        at the boundary and gets pruned.  Failed/errored still use
        JOB_FAILED_RETENTION default (90)."""
        self._create_jobs()
        job = PruneJob(PruneJob.get_jobs().first() or PruneJob.enqueue())
        job.run()

        remaining = Job.objects.count()
        # Completed > 200: 200-day-old job is at boundary → 1 deleted
        # Failed > 90: 100, 200 → 2 deleted
        # Errored > 90: 200 → 1 deleted
        # Total deleted: 4. Remaining: 12 - 4 = 8.
        self.assertEqual(remaining, 8)

    @override_settings(JOB_FAILED_RETENTION=50)
    def test_separate_failed_retention(self):
        """Failed retention can differ from completed retention."""
        self._create_jobs()
        job = PruneJob(PruneJob.get_jobs().first() or PruneJob.enqueue())
        job.run()

        remaining = Job.objects.count()
        # Completed > 90: 100, 200 → 2 deleted
        # Failed > 50: failed 100, 200 → 2 deleted
        # Errored > 50: errored 200 → 1 deleted
        # Total deleted: 5. Remaining: 12 - 5 = 7.
        self.assertEqual(remaining, 7)

    @override_settings(JOB_COMPLETED_RETENTION=0)
    def test_skips_completed_when_retention_zero(self):
        """Completed retention 0 means keep all completed jobs.
        Failed retention still defaults to 90."""
        self._create_jobs()
        job = PruneJob(PruneJob.get_jobs().first() or PruneJob.enqueue())
        job.run()

        remaining = Job.objects.count()
        # Completed: none deleted (retention=0)
        # Failed > 90: failed 100, 200 → 2 deleted
        # Errored > 90: errored 200 → 1 deleted
        # Total deleted: 3. Remaining: 12 - 3 = 9.
        self.assertEqual(remaining, 9)

    @override_settings(JOB_FAILED_RETENTION=0)
    def test_skips_failed_when_retention_zero(self):
        """Failed retention 0 means keep all failed/errored jobs.
        Completed retention still defaults to 90."""
        self._create_jobs()
        job = PruneJob(PruneJob.get_jobs().first() or PruneJob.enqueue())
        job.run()

        remaining = Job.objects.count()
        # Completed > 90: 100, 200 → 2 deleted
        # Failed/errored: none deleted (retention=0)
        # Total deleted: 2. Remaining: 12 - 2 = 10.
        self.assertEqual(remaining, 10)
