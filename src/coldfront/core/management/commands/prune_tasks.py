# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import logging
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from coldfront.core.choices import JobStatusChoices
from coldfront.core.models import Job

logger = logging.getLogger("coldfront.prune_tasks")


def valid_positive_int(val: str) -> int:
    num = int(val)
    if num < 0:
        raise ValueError("Must be zero or greater")
    return num


class Command(BaseCommand):
    help = "Prune finished Job records according to a retention policy"

    def add_arguments(self, parser):
        parser.add_argument(
            "--queue-name",
            nargs="?",
            default="*",
            type=str,
            help="The queues to process. Separate multiple with a comma. "
            "To process all queues, use '*' (default: %(default)r)",
        )
        parser.add_argument(
            "--min-age-days",
            nargs="?",
            default=None,
            type=valid_positive_int,
            help="Minimum age (in days) of a finished job to be pruned. "
            "Overrides JOB_COMPLETED_RETENTION setting (default: %(default)r)",
        )
        parser.add_argument(
            "--failed-min-age-days",
            nargs="?",
            default=None,
            type=valid_positive_int,
            help="Minimum age (in days) of a failed/errored job to be pruned. "
            "Overrides JOB_FAILED_RETENTION setting (default: same as --min-age-days)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Don't delete, just show how many would be deleted",
        )

    def configure_logging(self, verbosity):
        if verbosity == 0:
            logger.setLevel(logging.WARNING)
        elif verbosity == 1:
            logger.setLevel(logging.INFO)
        else:
            logger.setLevel(logging.DEBUG)

        if not logger.hasHandlers():
            logger.addHandler(logging.StreamHandler(self.stdout))

    def handle(self, *, verbosity, queue_name, min_age_days, failed_min_age_days, dry_run, **options):
        self.configure_logging(verbosity)

        # Resolve retention values from settings or CLI overrides
        completed_retention = (
            min_age_days if min_age_days is not None else getattr(settings, "JOB_COMPLETED_RETENTION", 90)
        )
        failed_retention = (
            failed_min_age_days
            if failed_min_age_days is not None
            else getattr(settings, "JOB_FAILED_RETENTION", completed_retention)
        )

        # If retention is negative, skip pruning entirely
        if completed_retention < 0 and failed_retention < 0:
            logger.info("Retention policy is disabled (completed=%s, failed=%s)", completed_retention, failed_retention)
            return

        now = timezone.now()
        results = Job.objects.finished()

        # Filter by queue name(s)
        queue_names = queue_name.split(",")
        if "*" not in queue_names:
            results = results.filter(queue_name__in=queue_names)

        # Build age-based filter
        age_filters = []
        if completed_retention >= 0:
            cutoff = now - timedelta(days=completed_retention)
            age_filters.append(
                Q(
                    status__in=[
                        JobStatusChoices.STATUS_COMPLETED,
                    ],
                    completed__lte=cutoff,
                )
            )
        if failed_retention >= 0:
            cutoff = now - timedelta(days=failed_retention)
            age_filters.append(
                Q(
                    status__in=[
                        JobStatusChoices.STATUS_FAILED,
                        JobStatusChoices.STATUS_ERRORED,
                    ],
                    completed__lte=cutoff,
                )
            )

        if age_filters:
            # Combine multiple age filters with OR
            combined = age_filters[0]
            for af in age_filters[1:]:
                combined |= af
            results = results.filter(combined)
        else:
            results = results.none()

        if dry_run:
            logger.info("Would delete %d job record(s)", results.count())
        else:
            deleted, _ = results.delete()
            logger.info("Deleted %d job record(s)", deleted)
