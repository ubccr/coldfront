# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

base_dir = settings.BASE_DIR


class Command(BaseCommand):
    help = "Run setup script to initialize the Coldfront database"

    def add_arguments(self, parser):
        parser.add_argument(
            "-f", "--force_overwrite", help="Force initial_setup script to run with no warning.", action="store_true"
        )

    def handle(self, *args, **options):
        if options["force_overwrite"]:
            run_setup()

        else:
            self.stdout.write(
                self.style.WARNING(
                    """WARNING: Running this command initializes the ColdFront database and may modify/delete data in your existing ColdFront database. This command is typically only run once."""
                )
            )
            user_response = input("Do you want to proceed?(yes):")

            if user_response == "yes":
                run_setup()
            else:
                self.stdout.write("Please enter 'yes' if you wish to run initial setup.")


def run_setup():
    call_command("migrate")
    call_command("import_field_of_science_data")
    call_command("add_default_grant_options")
    call_command("add_default_project_choices")
    call_command("add_resource_defaults")
    call_command("add_allocation_defaults")
    call_command("add_default_publication_sources")
    call_command("add_scheduled_tasks")
