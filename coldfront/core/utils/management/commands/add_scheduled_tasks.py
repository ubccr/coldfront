import datetime

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from django_q.models import Schedule
from django_q.tasks import schedule

base_dir = settings.BASE_DIR


class Command(BaseCommand):

    def handle(self, *args, **options):

        date = timezone.now() + datetime.timedelta(days=1)
        date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        # Cammenting out tasks that handle expiration, as we don't use expirations or end_dates.
        # schedule('coldfront.core.allocation.tasks.update_statuses',
        #          schedule_type=Schedule.DAILY,
        #          next_run=date)

        # schedule('coldfront.core.allocation.tasks.send_expiry_emails',
        #          schedule_type=Schedule.DAILY,
        #          next_run=date)

        # if plugins are installed, add their tasks
        kwargs = {  "repeats":-1, }
        plugins = ['fasrc', 'sftocf']
        if all(f'coldfront.plugins.{plugin}' in settings.INSTALLED_APPS for plugin in plugins):
            import json
            with open("coldfront/plugins/sftocf/servers.json", "r") as myfile:
                svp = json.loads(myfile.read())
            volumes = [k for vol in svp.values() for k in vol.keys()]
            vol_date = date
            for volume in volumes:
                vol_date = vol_date + datetime.timedelta(days=1)
                schedule('coldfront.plugins.sftocf.tasks.pull_sf_push_cf',
                    volume,
                    next_run=vol_date,
                    schedule_type=Schedule.WEEKLY,
                    **kwargs)
                schedule('coldfront.plugins.fasrc.tasks.import_quotas',
                    volume,
                    next_run=vol_date + datetime.timedelta(hours=1),
                    schedule_type=Schedule.WEEKLY,
                    **kwargs
                )
