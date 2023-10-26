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
        plugins_tasks = {
            'fasrc': ['import_quotas', 'id_import_allocations'],
            'sftocf': ['pull_sf_push_cf_redash', 'pull_resource_data'],
            'ldap': ['update_group_membership_ldap', 'id_add_projects'],
        }
        scheduled = [task.func for task in Schedule.objects.all()]

        for plugin, tasks in plugins_tasks.items():
            if f'coldfront.plugins.{plugin}' in settings.INSTALLED_APPS:
                for task in tasks:
                    if f'coldfront.plugins.{plugin}.tasks.{task}' not in scheduled:
                        schedule(f'coldfront.plugins.{plugin}.tasks.{task}',
                            next_run=date,
                            schedule_type=Schedule.DAILY,
                            **kwargs)

        if f'coldfront.core.allocation.tasks.send_request_reminder_emails' not in scheduled:
            schedule(
                f'coldfront.core.allocation.tasks.send_request_reminder_emails',
                next_run=date,
                schedule_type=Schedule.WEEKLY,
                **kwargs
            )
