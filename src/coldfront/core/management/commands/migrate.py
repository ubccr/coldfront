# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Custom migrate command that detects v1.1.x databases and aborts before running
migrations. This prevents accidental unsupported migrations from older v1.1.x
versions of ColdFront. In order to upgrade to v2, sites can export their v1
database to YAML and import via coldfront_initializer instead.
"""

import sys

from django.core.management.commands.migrate import Command as MigrateCommand
from django.db import DatabaseError, connection

# Tables unique to v1.1.x that will not exist in v2.0.x
V1_TABLES = frozenset(
    {
        # allocation app
        "allocation_allocation",
        "allocation_allocationstatuschoice",
        "allocation_allocationadminnote",
        "allocation_allocationusernote",
        "allocation_allocationuser",
        "allocation_allocationaccount",
        "allocation_allocationattribute",
        "allocation_allocationattributetype",
        "allocation_allocationattributeusage",
        "allocation_allocationuserstatuschoice",
        "allocation_allocationchangestatuschoice",
        "allocation_allocationchangerequest",
        "allocation_allocationattributechangerequest",
        "allocation_attributetype",
        "allocation_historicalallocation",
        "allocation_historicalallocationuser",
        "allocation_historicalallocationattribute",
        "allocation_historicalallocationattributetype",
        "allocation_historicalallocationattributeusage",
        "allocation_historicalallocationchangerequest",
        "allocation_historicalallocationattributechangerequest",
        # project app
        "project_project",
        "project_projectstatuschoice",
        "project_projectuserrolechoice",
        "project_projectuserstatuschoice",
        "project_projectuser",
        "project_projectusermessage",
        "project_projectreview",
        "project_projectreviewstatuschoice",
        "project_projectadmincomment",
        "project_projectattribute",
        "project_projectattributetype",
        "project_projectattributeusage",
        "project_attributetype",
        "project_historicalproject",
        "project_historicalprojectuser",
        "project_historicalprojectreview",
        "project_historicalprojectattribute",
        "project_historicalprojectattributetype",
        "project_historicalprojectattributeusage",
        # resource app
        "resource_resource",
        "resource_resourcetype",
        "resource_resourceattribute",
        "resource_resourceattributetype",
        "resource_attributetype",
        "resource_historicalresource",
        "resource_historicalresourcetype",
        "resource_historicalresourceattribute",
        "resource_historicalresourceattributetype",
        # field_of_science app
        "field_of_science_fieldofscience",
        # user app
        "user_userprofile",
        # grant app
        "grant_grant",
        "grant_grantfundingagency",
        "grant_grantstatuschoice",
        "grant_historicalgrant",
        # publication app
        "publication_publication",
        "publication_publicationsource",
        "publication_historicalpublication",
        # research_output app
        "research_output_researchoutput",
        "research_output_historicalresearchoutput",
    }
)

MESSAGE = """\
ERROR: Detected ColdFront v1.1.x database. The v2.0.x schema is incompatible.
Do NOT run migrations directly on an existing v1 database.

To upgrade, export your v1 database to YAML:
    uv run coldfront dumpdata --all > coldfront_v1.yaml

Then import into a fresh v2 database using coldfront_initializer:
    # Set up a new empty database first, then:
    uv run coldfront initial_setup
    uv run coldfront load_test_data   # or use coldfront_initializer import

Aborting.
"""


class Command(MigrateCommand):
    """
    Custom migrate command that detects v1.1.x databases and aborts before
    running migrations.
    """

    help = f"{MigrateCommand.help}"

    def execute(self, *args, **options):
        self._check_for_v1_database()
        return super().execute(*args, **options)

    def _check_for_v1_database(self):
        """Exit with error if the database contains v1.1.x tables."""
        try:
            tables = connection.introspection.table_names()
        except DatabaseError:
            # Database doesn't exist yet or can't be queried — no v1 to detect
            return

        detected = [t for t in tables if t in V1_TABLES]
        if detected:
            self.stderr.write(self.style.ERROR(MESSAGE))
            self.stderr.write(
                self.style.WARNING(
                    f"Detected v1 tables: {', '.join(sorted(detected)[:10])}" + ("..." if len(detected) > 10 else "")
                )
            )
            sys.exit(1)
