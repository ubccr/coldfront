from django.core.management.base import BaseCommand

from django_q.models import Schedule

from coldfront.plugins.qumulo.tasks import (
    poll_ad_groups,
    conditionally_update_storage_allocation_statuses,
)


class Command(BaseCommand):
    def handle(self, *args, **options):
        print("Scheduling AD Poller")
        Schedule.objects.get_or_create(
            func="coldfront.plugins.qumulo.management.commands.add_scheduled_ad_poller.sequential_poll_and_check",
            name="Update Pending Allocations",
            schedule_type=Schedule.MINUTES,
            minutes=1,
            repeats=-1,
        )


def sequential_poll_and_check() -> None:
    poll_ad_groups()
    conditionally_update_storage_allocation_statuses()
