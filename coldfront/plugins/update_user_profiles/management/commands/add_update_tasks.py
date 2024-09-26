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

        date = date + datetime.timedelta(days=-1*(date.weekday()-5))
        schedule('coldfront.plugins.update_user_profiles.tasks.run_update_user_profiles',
                 schedule_type=Schedule.WEEKLY,
                 next_run=date)
