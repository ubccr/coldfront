from django.core.management.base import BaseCommand

from django_q.tasks import async_chain

from coldfront_plugin_qumulo.tasks import (
    poll_ad_groups,
    conditionally_update_storage_allocation_statuses,
)


class Command(BaseCommand):
    help = (
        "Run Active Directory poller to update ACL allocations and storage allocations"
    )

    def handle(self, *args, **options):
        print("Running AD Poller")
        async_chain(
            [(poll_ad_groups), (conditionally_update_storage_allocation_statuses)]
        )
