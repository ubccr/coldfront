import arrow
from django.core.management.base import BaseCommand

from django_q.tasks import schedule

from django_q.models import Schedule

from coldfront.plugins.qumulo.utils.eib_billing import EIBBilling

SCHEDULED_FOR_2ND_DAY_OF_MONTH_AT_6_30_AM = (
    arrow.utcnow().replace(day=2, hour=6, minute=30).format(arrow.FORMAT_RFC3339)
)


class Command(BaseCommand):

    def handle(self, *args, **options):
        print("Scheduling generating storage2 monthly billing report")
        schedule(
            func="coldfront.plugins.qumulo.management.commands.add_scheduled_generate_billing_report_monthly.generate_storage2_monthly_billing_report",
            name="Generate Storage2 Monthly Billing Report",
            schedule_type=Schedule.MONTHLY,
            next_run=SCHEDULED_FOR_2ND_DAY_OF_MONTH_AT_6_30_AM,
        )


def generate_storage2_monthly_billing_report() -> None:
    eib_billing = EIBBilling()
    eib_billing.generate_monthly_billing_report()
