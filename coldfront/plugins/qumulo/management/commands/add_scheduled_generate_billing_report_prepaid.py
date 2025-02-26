import arrow
from django.core.management.base import BaseCommand

from django_q.tasks import schedule

from django_q.models import Schedule

from datetime import datetime, timezone

from coldfront.plugins.qumulo.utils.prepaid_billing import PrepaidBilling

SCHEDULED_FOR_28TH_DAY_OF_MONTH_AT_6_30_AM = (
    arrow.utcnow().replace(day=28, hour=6, minute=30).format(arrow.FORMAT_RFC3339)
)


class Command(BaseCommand):

    def handle(self, *args, **options):
        print("Scheduling generating storage2 monthly prepaid billing report")
        schedule(
            func="coldfront.plugins.qumulo.management.commands.add_scheduled_generate_billing_report_prepaid.generate_storage2_prepaid_billing_report",
            name="Generate Prepaid Billing Report",
            schedule_type=Schedule.MONTHLY,
            next_run=SCHEDULED_FOR_28TH_DAY_OF_MONTH_AT_6_30_AM,
        )


def generate_storage2_prepaid_billing_report() -> None:
    prepaid_billing = PrepaidBilling(datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    prepaid_billing.generate_prepaid_billing_report()
