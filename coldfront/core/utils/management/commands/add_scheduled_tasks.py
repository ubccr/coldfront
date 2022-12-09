from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from django_q.models import Schedule
from django_q.tasks import schedule

base_dir = settings.BASE_DIR


class Command(BaseCommand):

    def handle(self, *args, **options):

        date = timezone.now()# + datetime.timedelta(days=1)
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
            scheduled = [task.func for task in Schedule.objects.all()]
            for func in ('coldfront.plugins.sftocf.tasks.pull_sf_push_cf_redash',
                        'coldfront.plugins.fasrc.tasks.import_quotas'):
                if func not in scheduled:
                    schedule(func,
                        next_run=date,
                        schedule_type=Schedule.DAILY,
                        **kwargs)
