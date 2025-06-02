# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import datetime

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from django_q.models import Schedule
from django_q.tasks import schedule

from coldfront.config.email import EMAIL_ALLOCATION_EULA_REMINDERS
from coldfront.core.utils.common import import_from_settings

ALLOCATION_EULA_ENABLE = import_from_settings("ALLOCATION_EULA_ENABLE", False)
base_dir = settings.BASE_DIR


class Command(BaseCommand):
    def handle(self, *args, **options):
        date = timezone.now() + datetime.timedelta(days=1)
        date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        schedule("coldfront.core.allocation.tasks.update_statuses", schedule_type=Schedule.DAILY, next_run=date)

        schedule("coldfront.core.allocation.tasks.send_expiry_emails", schedule_type=Schedule.DAILY, next_run=date)

        if ALLOCATION_EULA_ENABLE and EMAIL_ALLOCATION_EULA_REMINDERS:
            schedule(
                "coldfront.core.allocation.tasks.send_eula_reminders", schedule_type=Schedule.WEEKLY, next_run=date
            )
