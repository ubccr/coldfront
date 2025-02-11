from django.core.management.base import BaseCommand

from django_q.models import Schedule

from coldfront.plugins.qumulo.management.commands.check_billing_cycles import (
    check_allocation_billing_cycle_and_prepaid_exp,
)


class Command(BaseCommand):
    def handle(self, *args, **options):
        print("Scheduling Prepaid Expiration Date Scanner")
        Schedule.objects.get_or_create(
            func="coldfront.plugins.qumulo.management.commands.add_scheduled_billing_cycle_check.prepaid_expiration_cleanup",
            name="Check Billing Statuses",
            schedule_type=Schedule.DAILY,
            repeats=-1,
        )


def prepaid_expiration_cleanup() -> None:
    check_allocation_billing_cycle_and_prepaid_exp()
