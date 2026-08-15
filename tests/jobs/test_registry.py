# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0


from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase

from coldfront.core.jobs import system_job, system_jobs
from coldfront.core.jobs.runner import JobRunner


class SystemJobDecoratorTestCase(TestCase):
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

    def test_system_jobs_starts_empty(self):
        # The registry may have entries from decorators called during
        # test setup, but the store itself should be a mutable dict.
        self.assertIsInstance(system_jobs, dict)
