from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.utils.common import delete_scheduled_tasks
from coldfront.core.utils.common import display_time_zone_date_to_utc_datetime
from coldfront.core.utils.common import utc_now_offset_aware

from django.db.models.signals import post_delete
from django.db.models.signals import post_save
import django.dispatch

from django_q.models import Schedule
from django_q.tasks import schedule

import logging


logger = logging.getLogger(__name__)


@django.dispatch.receiver(post_save, sender=AllocationPeriod)
def reschedule_allocation_renewal_scheduled_task(sender, instance, created,
                                                 **kwargs):
    """When an AllocationPeriod is saved, delete any scheduled tasks for
    starting it and schedule a new one if its start date is in the
    future."""
    func = 'django.core.management.call_command'
    args = ('start_allocation_period', instance.pk)

    delete_scheduled_tasks(func, *args)

    next_run = display_time_zone_date_to_utc_datetime(instance.start_date)
    if next_run > utc_now_offset_aware():
        kwargs = {
            'next_run': next_run,
            'repeats': -1,
            'schedule_type': Schedule.ONCE,
        }
        schedule(func, *args, **kwargs)

    message = (
        f'Scheduled a task for starting AllocationPeriod {instance.pk} to run '
        f'at {next_run}.')
    logger.info(message)


@django.dispatch.receiver(post_delete, sender=AllocationPeriod)
def delete_allocation_renewal_scheduled_task(sender, instance, **kwargs):
    """When an AllocationPeriod is deleted, delete any scheduled tasks
    for starting it."""
    func = 'django.core.management.call_command'
    args = ('start_allocation_period', instance.pk)

    delete_scheduled_tasks(func, *args)
