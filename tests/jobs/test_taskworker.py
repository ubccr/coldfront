# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings


class TaskWorkerCommandTestCase(TestCase):
    def test_command_registers_system_jobs_with_db_backend(self):
        with patch("coldfront.core.management.commands.taskworker.system_jobs") as mock_jobs:
            mock_jobs.items.return_value = []
            with patch("coldfront.core.management.commands.taskworker.call_command") as mock_call:
                call_command("taskworker", queue=["default"])
                mock_call.assert_called_once_with(
                    "db_worker",
                    queue_name="default",
                    interval=1.0,
                )

    def test_command_with_multiple_queues_db_backend(self):
        with patch("coldfront.core.management.commands.taskworker.system_jobs") as mock_jobs:
            mock_jobs.items.return_value = []
            with patch("coldfront.core.management.commands.taskworker.call_command") as mock_call:
                call_command("taskworker", queue=["default", "slurm", "email"])
                mock_call.assert_called_once_with(
                    "db_worker",
                    queue_name="default,slurm,email",
                    interval=1.0,
                )

    def test_command_registers_system_jobs_at_startup(self):
        class MockRunner:
            name = "MockRunner"

            @classmethod
            def enqueue_once(cls, interval=None):
                pass

        with patch("coldfront.core.management.commands.taskworker.system_jobs") as mock_jobs:
            mock_jobs.items.return_value = [
                (MockRunner, {"interval": 15}),
            ]
            with patch("coldfront.core.management.commands.taskworker.call_command"):
                with patch.object(MockRunner, "enqueue_once") as mock_enqueue:
                    call_command("taskworker", queue=["default"])
                    mock_enqueue.assert_called_once_with(interval=15)

    def test_command_default_queue(self):
        with patch("coldfront.core.management.commands.taskworker.system_jobs") as mock_jobs:
            mock_jobs.items.return_value = []
            with patch("coldfront.core.management.commands.taskworker.call_command") as mock_call:
                call_command("taskworker")
                mock_call.assert_called_once_with(
                    "db_worker",
                    queue_name="default",
                    interval=1.0,
                )

    @override_settings(COLDFRONT_TASKS_BACKEND="django_tasks_rq.backend.RQBackend")
    def test_command_with_rq_backend_delegates_to_rqworker(self):
        with patch("coldfront.core.management.commands.taskworker.system_jobs") as mock_jobs:
            mock_jobs.items.return_value = []
            with patch("coldfront.core.management.commands.taskworker.call_command") as mock_call:
                call_command("taskworker", queue=["default"])
                mock_call.assert_called_once_with("rqworker", queue=["default"])
