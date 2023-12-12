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
        schedule('coldfront.plugins.slate_project.tasks.sync_all_slate_project_allocations',
                 schedule_type=Schedule.DAILY,
                 next_run=date)

        date = date.replace(month=date.month % 12 + 1, day=1)
        schedule('coldfront.plugins.slate_project.tasks.send_inactive_user_email_report',
                 schedule_type=Schedule.MONTHLY,
                 next_run=date)
