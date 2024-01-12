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

        schedule('coldfront.plugins.slate_project.tasks.send_ineligible_pi_email_report',
                 schedule_type=Schedule.DAILY,
                 next_run=date)
        
        schedule('coldfront.plugins.slate_project.tasks.import_slate_projects',
                 schedule_type=Schedule.DAILY,
                 next_run=date)

        current_month = date.month
        next_month = current_month % 12 + 1
        if next_month < current_month:
            date = date.replace(year=date.year + 1, month=next_month, day=1)
        else:
            date = date.replace(month=next_month, day=1)
        schedule('coldfront.plugins.slate_project.tasks.send_inactive_user_email_report',
                 schedule_type=Schedule.MONTHLY,
                 next_run=date)
