# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import logging
import math
import os
import random
import signal
import sys
import time
from argparse import ArgumentTypeError, BooleanOptionalAction

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import close_old_connections
from django.db.utils import OperationalError
from django.utils.autoreload import DJANGO_AUTORELOAD_ENV, run_with_reloader
from django_tasks import DEFAULT_TASK_QUEUE_NAME, task_backends
from django_tasks.base import TaskContext
from django_tasks.signals import task_finished, task_started
from django_tasks.utils import get_random_id

from coldfront.core.models import Job
from coldfront.core.tasks.backends.coldfront import ColdFrontBackend

logger = logging.getLogger("coldfront.db_worker")


def valid_backend_name(val):
    try:
        backend = task_backends[val]
    except KeyError as e:
        raise ArgumentTypeError(e.args[0]) from e
    if not isinstance(backend, ColdFrontBackend):
        raise ArgumentTypeError(f"Backend '{val}' is not a ColdFront DB backend")
    return val


def valid_interval(val):
    num = float(val)
    if not math.isfinite(num):
        raise ArgumentTypeError("Must be a finite floating point value")
    if num < 0:
        raise ArgumentTypeError("Must be zero or greater")
    return num


def valid_positive_int(val):
    num = int(val)
    if num <= 0:
        raise ArgumentTypeError("Must be greater than zero")
    return num


def validate_worker_id(val):
    if not val:
        raise ArgumentTypeError("Worker id must not be empty")
    if len(val) > 64:
        raise ArgumentTypeError("Worker ids must be shorter than 64 characters")
    return val


class Worker:
    def __init__(
        self,
        *,
        queue_names,
        interval,
        batch,
        startup_delay,
        max_tasks,
        worker_id,
        excluded_queue_names,
    ):
        self.queue_names = queue_names
        self.process_all_queues = "*" in queue_names
        self.excluded_queue_names = excluded_queue_names
        self.interval = interval
        self.batch = batch
        self.startup_delay = startup_delay
        self.max_tasks = max_tasks

        self.running = True
        self.running_task = False
        self._run_tasks = 0
        self.worker_id = worker_id

    def shutdown(self, signum, frame):
        if not self.running:
            logger.warning("Received %s - terminating current task.", signal.strsignal(signum))
            self.reset_signals()
            sys.exit(1)

        logger.warning(
            "Received %s - shutting down gracefully... (press Ctrl+C again to force)",
            signal.strsignal(signum),
        )
        self.running = False

        if not self.running_task:
            sys.exit(0)

    def configure_signals(self):
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)
        if hasattr(signal, "SIGQUIT"):
            signal.signal(signal.SIGQUIT, self.shutdown)

    def reset_signals(self):
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        if hasattr(signal, "SIGQUIT"):
            signal.signal(signal.SIGQUIT, signal.SIG_DFL)

    def run(self):
        logger.info(
            "Starting worker worker_id=%s queues=%s",
            self.worker_id,
            ",".join(self.queue_names),
        )

        if self.startup_delay and self.interval:
            time.sleep(random.random())

        while self.running:
            close_old_connections()

            jobs = Job.objects.ready()
            if not self.process_all_queues:
                jobs = jobs.filter(queue_name__in=self.queue_names)
            if self.excluded_queue_names:
                jobs = jobs.exclude(queue_name__in=self.excluded_queue_names)

            try:
                job = jobs.get_locked()
            except OperationalError as e:
                if "is locked" in e.args[0]:
                    job = None
                else:
                    raise

            if job is not None:
                self.run_job(job)

            if self.batch and job is None:
                logger.info(
                    "No more tasks to run for worker_id=%s - exiting gracefully.",
                    self.worker_id,
                )
                return None

            if self.max_tasks is not None and self._run_tasks >= self.max_tasks:
                logger.info(
                    "Run maximum tasks (%d) on worker=%s - exiting gracefully.",
                    self._run_tasks,
                    self.worker_id,
                )
                return None

            close_old_connections()

            if self.running and not job:
                time.sleep(self.interval)

    def run_job(self, job):
        """Execute a Job and record its outcome."""
        try:
            self.running_task = True
            task = job.task
            task_result = job.task_result

            backend_type = type(task.get_backend())

            job.claim(self.worker_id)
            task_started.send(sender=backend_type, task_result=task_result)

            # If the task is a ``JobRunner`` bound method, reconstruct the
            # call via ``cls.handle(job, ...)`` instead of ``task.call()``,
            # which would miss the implicit ``cls`` argument.
            runner_cls_path = task_result.kwargs.pop("_runner_cls_path", None)
            if runner_cls_path:
                from django.utils.module_loading import import_string

                runner_cls = import_string(runner_cls_path)
                return_value = runner_cls.handle(
                    job,
                    *task_result.args,
                    **task_result.kwargs,
                )
            elif task.takes_context:
                return_value = task.call(
                    TaskContext(task_result=task_result),
                    *task_result.args,
                    **task_result.kwargs,
                )
            else:
                return_value = task.call(*task_result.args, **task_result.kwargs)

            job.set_successful(return_value)
            task_finished.send(sender=backend_type, task_result=job.task_result)
        except BaseException as e:
            job.set_failed(e)
            try:
                sender = type(job.task.get_backend())
                task_result = job.task_result
            except Exception:
                logger.exception("Job id=%s failed unexpectedly", job.id)
            else:
                task_finished.send(
                    sender=sender,
                    task_result=task_result,
                )
        finally:
            self.running_task = False
            self._run_tasks += 1


class Command(BaseCommand):
    help = "Run a database background worker for ColdFront jobs"

    def add_arguments(self, parser):
        parser.add_argument(
            "--queue-name",
            nargs="?",
            default=DEFAULT_TASK_QUEUE_NAME,
            type=str,
            help="The queues to process. Separate multiple with a comma. To process all queues, use '*' (default: %(default)r)",
        )
        parser.add_argument(
            "--exclude-queues",
            nargs="?",
            default="",
            type=str,
            help="Queues to exclude. Separate multiple with a comma.",
        )
        parser.add_argument(
            "--interval",
            nargs="?",
            default=1,
            type=valid_interval,
            help="The interval (in seconds) to wait, when there are no tasks in the queue, before checking for tasks again (default: %(default)r)",
        )
        parser.add_argument(
            "--batch",
            action="store_true",
            help="Process all outstanding tasks, then exit. Can be used in combination with --max-tasks.",
        )
        parser.add_argument(
            "--reload",
            action=BooleanOptionalAction,
            default=settings.DEBUG,
            help="Reload the worker on code changes. Not recommended for production as tasks may not be stopped cleanly (default: DEBUG)",
        )
        parser.add_argument(
            "--no-startup-delay",
            action="store_false",
            dest="startup_delay",
            help="Don't add a small delay at startup.",
        )
        parser.add_argument(
            "--max-tasks",
            nargs="?",
            default=None,
            type=valid_positive_int,
            help="If provided, the maximum number of tasks the worker will execute before exiting.",
        )
        parser.add_argument(
            "--worker-id",
            nargs="?",
            type=validate_worker_id,
            help="Worker id. MUST be unique across worker pool (default: auto-generate)",
            default=get_random_id(),
        )

    def configure_logging(self, verbosity):
        if verbosity == 0:
            logger.setLevel(logging.CRITICAL)
        elif verbosity == 1:
            logger.setLevel(logging.INFO)
        else:
            logger.setLevel(logging.DEBUG)

        if not logger.hasHandlers():
            logger.addHandler(logging.StreamHandler(self.stdout))

    def handle(
        self,
        *,
        verbosity,
        queue_name,
        interval,
        batch,
        startup_delay,
        reload,
        max_tasks,
        worker_id,
        exclude_queues,
        **options,
    ):
        self.configure_logging(verbosity)

        queue_names = queue_name.split(",")
        excluded_queue_names = exclude_queues.split(",") if exclude_queues else []

        if excluded_queue_names and "*" not in queue_names:
            self.stderr.write("--exclude-queues can only be used with --queue-name=*")
            return

        worker = Worker(
            queue_names=queue_names,
            interval=interval,
            batch=batch,
            startup_delay=startup_delay,
            max_tasks=max_tasks,
            worker_id=worker_id,
            excluded_queue_names=excluded_queue_names,
        )

        if reload:
            if os.environ.get(DJANGO_AUTORELOAD_ENV) == "true":
                worker.configure_signals()
            run_with_reloader(worker.run)
        else:
            worker.configure_signals()
            worker.run()
