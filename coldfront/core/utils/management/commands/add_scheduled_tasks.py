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
        kwargs = {"repeats": -1,}
        plugins_tasks = {
            'fasrc': [
                ('import_allocation_filepaths', (1,0)),
                ('id_import_allocations', (1,15)),
                ('import_quotas', (1,30)),
                ('pull_resource_data', (0,0)),
            ],
            'sftocf': [
                ('pull_sf_push_cf', (1,45)),
                ('update_zones', (6,25)),
            ],
            # 'lfs': ['pull_lfs_filesystem_stats'],
            'ldap': [
                ('update_group_membership_ldap', (12,45)),
                ('id_add_projects', (1,0)),
            ],
            'slurm': [('slurm_sync', (3,0))],
            'xdmod': [('xdmod_usage', (3,30))],
        }
        scheduled = [task.func for task in Schedule.objects.all()]

        for plugin, tasks in plugins_tasks.items():
            if f'coldfront.plugins.{plugin}' in settings.INSTALLED_APPS:
                for task in tasks:
                    tname = task[0]
                    ttime = task[1]
                    date = date.replace(hour=ttime[0], minute=ttime[1], second=0, microsecond=0)
                    if f'coldfront.plugins.{plugin}.tasks.{task}' not in scheduled:
                        schedule(f'coldfront.plugins.{plugin}.tasks.{task}',
                            next_run=date,
                            schedule_type=Schedule.DAILY,
                            name=tname,
                            **kwargs)

        if 'coldfront.core.allocation.tasks.send_request_reminder_emails' not in scheduled:
            schedule(
                'coldfront.core.allocation.tasks.send_request_reminder_emails',
                next_run=date,
                schedule_type=Schedule.WEEKLY,
                **kwargs
            )
