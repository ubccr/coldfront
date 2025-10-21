# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django_q.models import Schedule
from django_q.tasks import schedule


class Command(BaseCommand):
    def handle(self, *args, **options):
        date = timezone.now() + datetime.timedelta(minutes=5)
        schedule(
            "coldfront.plugins.maintenance_mode.tasks.check_maintenance",
            schedule_type=Schedule.MINUTES,
            minutes=1,
            repeats=-1,
            name="maintenance_mode_checker",
            next_run=date,
        )
