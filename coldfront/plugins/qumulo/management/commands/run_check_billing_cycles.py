from django.core.management.base import BaseCommand

from django_q.tasks import async_chain

from coldfront.plugins.qumulo.management.commands.check_billing_cycles import (
    check_allocation_billing_cycle_and_prepaid_exp,
)


class Command(BaseCommand):
    help = "Run Check Billing Cycles to update billing cycles and prepaid expiration"

    def handle(self, *args, **options):
        print("Running Billing Cycle and Prepaid Expiration Check")
        async_chain(
            [
                (check_allocation_billing_cycle_and_prepaid_exp),
            ]
        )
