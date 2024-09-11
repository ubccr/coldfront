from coldfront_plugin_qumulo.utils.active_directory_api import ActiveDirectoryAPI
from django.core.management.base import BaseCommand, CommandParser

import os
from dotenv import load_dotenv

load_dotenv(override=True)


class Command(BaseCommand):
    help = "Cleans any Active Directory Groups from QA Server that match the provided string.\nRefer to ldap3 documentation for search string format"

    def handle(self, *args, **options):
        groups_OU = os.environ.get("AD_GROUPS_OU")
        if "OU=QA" not in groups_OU:
            print(
                """INVALID ENV: This script can only be run on servers configured for access to Active Directory's QA O.U."""
            )
            return

        print(
            """WARNING: Run with care!!!  Incorrect usage could result in unintended Active Directory resources being deleted.  Only use to delete testing data."""
        )
        search_str = input("Provide search string:")

        active_directory_api = ActiveDirectoryAPI()

        active_directory_api.conn.search(
            "dc=accounts,dc=ad,dc=wustl,dc=edu", f"(cn={search_str})"
        )

        groups = active_directory_api.conn.response

        for group in groups:
            cn = next(
                filter(lambda element: element.startswith("CN"), group["dn"].split(","))
            )

            user_choice = input(
                f"The following group will be deleted: {cn}.  Are you sure?(yes)"
            )

            if user_choice == "yes":
                active_directory_api.conn.delete(group["dn"])
            else:
                print(f"Skipping deletion of {cn}")
