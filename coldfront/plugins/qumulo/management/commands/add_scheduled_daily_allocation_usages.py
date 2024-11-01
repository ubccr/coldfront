import arrow
from django.core.management.base import BaseCommand

from django_q.tasks import schedule

from django_q.models import Schedule

from coldfront.plugins.qumulo.tasks import ingest_quotas_with_daily_usage

SCHEDULED_FOR_2_30_AM = (
    arrow.utcnow().replace(hour=2, minute=30).format(arrow.FORMAT_RFC3339)
)


class Command(BaseCommand):

    def handle(self, *args, **options):
        print("Scheduling polling daily usage from QUMULO")
        schedule(
            "coldfront.plugins.qumulo.management.commands.add_scheduled_daily_allocation_usages.poll_allocation_daily_usages",
            name="Ingest Allocation Daily Usages",
            schedule_type=Schedule.DAILY,
            next_run=SCHEDULED_FOR_2_30_AM,
        )


def poll_allocation_daily_usages() -> None:
    ingest_quotas_with_daily_usage()
