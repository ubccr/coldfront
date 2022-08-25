import datetime

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from django_q.models import Schedule
from django_q.tasks import schedule

base_dir = settings.BASE_DIR


class Command(BaseCommand):

    def handle(self, *args, **options):

        date = timezone.localtime() + datetime.timedelta(days=1)
        date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        schedule('coldfront.core.allocation.tasks.update_statuses',
                 schedule_type=Schedule.DAILY,
                 next_run=date)

        schedule('coldfront.core.allocation.tasks.send_expiry_emails',
                 schedule_type=Schedule.DAILY,
                 next_run=date)

        schedule('coldfront.core.project.tasks.update_statuses',
                 schedule_type=Schedule.DAILY,
                 next_run=date)

        schedule('coldfront.core.project.tasks.send_expiry_emails',
                 schedule_type=Schedule.DAILY,
                 next_run=date)

        schedule('coldfront.plugins.slurm.tasks.run_slurm_dump',
                 schedule_type=Schedule.HOURLY)
