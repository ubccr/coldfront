# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import os

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils.autoreload import DJANGO_AUTORELOAD_ENV

from coldfront.core.jobs.registry import system_jobs


def _is_db_backend():
    """Return True if COLDFRONT_TASKS_BACKEND points to the DB backend."""
    backend_path = getattr(
        settings,
        "COLDFRONT_TASKS_BACKEND",
        "django_tasks_db.backend.DatabaseBackend",
    )
    return "django_tasks_rq" not in backend_path


class Command(BaseCommand):
    help = "Start background task workers for ColdFront jobs"

    def add_arguments(self, parser):
        parser.add_argument(
            "--queue",
            nargs="+",
            default=["default"],
            help="Name(s) of the queue(s) to service (default: 'default')",
        )
        parser.add_argument(
            "--interval",
            type=float,
            default=1.0,
            help="Polling interval (seconds) for the DB worker; ignored for RQ (default: 1.0)",
        )

    def handle(self, *args, **options):
        queues = options["queue"]
        interval = options["interval"]

        # Register system jobs at startup. Because enqueue_once() is
        # idempotent, calling it on every worker startup is safe even
        # if another worker already registered the schedules.
        for runner_cls, config in system_jobs.items():
            runner_cls.enqueue_once(interval=config["interval"])

        # Skip the startup message when the reloader has already launched
        # the worker — otherwise it appears twice (parent + child process).
        if os.environ.get(DJANGO_AUTORELOAD_ENV) != "true":
            self.stdout.write(self.style.NOTICE(f"Starting task worker(s) for queue(s): {', '.join(queues)}"))

        if _is_db_backend():
            # Delegate to ColdFront's db_worker management command
            call_command(
                "db_worker",
                queue_name=",".join(queues),
                interval=interval,
            )
        else:
            # Delegate to django-rq's rqworker management command
            call_command("rqworker", queue=queues)
