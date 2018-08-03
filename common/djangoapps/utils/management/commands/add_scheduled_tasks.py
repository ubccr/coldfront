import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django_q.models import Schedule
from django_q.tasks import schedule
import datetime


base_dir = settings.BASE_DIR


class Command(BaseCommand):

    def handle(self, *args, **options):

        date = datetime.datetime.now() + datetime.timedelta(days=1)
        schedule('common.djangolibs.utils.update_statuses',
            schedule_type=Schedule.DAILY,
            next_run=datetime.datetime(date.year, date.month, date.day, 00, 00, 00, 000000))
