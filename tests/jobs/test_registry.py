# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0


from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase

from coldfront.core.jobs import system_job, system_jobs
from coldfront.core.jobs.runner import JobRunner


class SystemJobDecoratorTestCase(TestCase):
    def setUp(self):
        # Snapshot the registry so test-local registrations cannot leak into
        # other tests; restore it afterwards. Mutate in place — the dict is
        # shared by reference across modules.
        self._original_jobs = dict(system_jobs)

    def tearDown(self):
        system_jobs.clear()
        system_jobs.update(self._original_jobs)

    def test_decorator_registers_runner(self):
        @system_job(interval=15)
        class MySyncJob(JobRunner):
            def run(self):
                pass

        self.assertIn(MySyncJob, system_jobs)
        self.assertEqual(system_jobs[MySyncJob]["interval"], 15)

    def test_decorator_requires_int_interval(self):
        with self.assertRaises(ImproperlyConfigured):

            @system_job(interval="not_an_int")
            class BadJob(JobRunner):
                def run(self):
                    pass

    def test_decorator_requires_positive_int(self):
        with self.assertRaises(ImproperlyConfigured):

            @system_job(interval=-1)
            class NegativeJob(JobRunner):
                def run(self):
                    pass

    def test_multiple_system_jobs(self):
        @system_job(interval=15)
        class SyncJobA(JobRunner):
            def run(self):
                pass

        @system_job(interval=1440)
        class SyncJobB(JobRunner):
            def run(self):
                pass

        self.assertIn(SyncJobA, system_jobs)
        self.assertIn(SyncJobB, system_jobs)
        self.assertEqual(system_jobs[SyncJobA]["interval"], 15)
        self.assertEqual(system_jobs[SyncJobB]["interval"], 1440)

    def test_system_jobs_registry_is_dict(self):
        self.assertIsInstance(system_jobs, dict)

    def test_system_jobs_baseline(self):
        """Only ColdFront's own system jobs are registered (no test pollution).

        The baseline is fixed at startup: core system jobs via
        ``coldfront.core.apps``, Slurm jobs via ``coldfront.slurm.apps``, and
        the RAS prune job via ``coldfront.ras.apps``.
        """
        from coldfront.core.tasks.system import NotificationDigestJob, PruneChangeLogJob, PruneJob
        from coldfront.ras.jobs import PruneProjectInviteJob
        from coldfront.slurm.jobs import SlurmSyncJob, SlurmUsageSyncJob

        expected = {
            PruneChangeLogJob,
            PruneJob,
            NotificationDigestJob,
            PruneProjectInviteJob,
            SlurmSyncJob,
            SlurmUsageSyncJob,
        }
        self.assertEqual(set(system_jobs), expected)
        for config in system_jobs.values():
            self.assertTrue(config)
            self.assertFalse(set(config) - {"interval", "cron_schedule"})
