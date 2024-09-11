from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run setup script to initialize the Coldfront database"

    def handle(self, *args, **options):
        print("Running Coldfront Plugin Qumulo setup script")
        call_base_commands()
        call_command("add_scheduled_ad_poller")
        call_command("add_scheduled_daily_allocation_usages")
        print("Coldfront Plugin Qumulo setup script complete")


def call_base_commands():
    call_command("add_qumulo_resource")
    call_command("add_qumulo_allocation_attribute_type")
    call_command("add_allocation_status")
