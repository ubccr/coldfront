import os
import logging
import datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django_q.models import Schedule
from django_q.tasks import schedule

base_dir = settings.BASE_DIR

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    def handle(self, *args, **options):

        date = timezone.now() + datetime.timedelta(minutes=1)
        kwargs = {  "repeats":-1, 
                    "next_run":date, 
                    "schedule_type": Schedule.DAILY }
        schedule('coldfront.plugins.sftocf.tasks.pull_sf_push_cf',
                    **kwargs)
        schedule('coldfront.plugins.fasrc.tasks.import_quotas',
                    **kwargs)
    
    
